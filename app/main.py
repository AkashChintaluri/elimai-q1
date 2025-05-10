from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import azure.cognitiveservices.speech as speechsdk
import pandas as pd
import json
import os
from typing import List, Dict
from pydantic import BaseModel
import tempfile
from pathlib import Path
from dotenv import load_dotenv
import logging
import soundfile as sf
import numpy as np
from scipy import signal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).parent / '.env'
logger.info(f"Loading .env file from: {env_path}")
load_dotenv(dotenv_path=env_path)

# Verify environment variables
speech_key = os.getenv("AZURE_SPEECH_KEY")
service_region = os.getenv("AZURE_SPEECH_REGION")
logger.info(f"Speech Key loaded: {'Yes' if speech_key else 'No'}")
logger.info(f"Service Region loaded: {'Yes' if service_region else 'No'}")

app = FastAPI(title="Medical Dictation API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

# Root endpoint to serve index.html
@app.get("/")
async def read_root():
    return FileResponse(str(Path(__file__).parent / "static" / "index.html"))

# Load medical terms database
MEDICAL_TERMS_PATH = Path(__file__).parent / "data" / "medical_terms.csv"
medical_terms_df = pd.read_csv(MEDICAL_TERMS_PATH)

class TranscriptionResponse(BaseModel):
    text: str
    structured_data: Dict[str, List[Dict[str, str]]]

def load_medical_terms():
    """Load and return medical terms from CSV file."""
    return medical_terms_df

def match_medical_terms(text: str) -> Dict[str, List[Dict[str, str]]]:
    """Match transcribed text with medical terms and return structured data."""
    result = {
        "lab_tests": [],
        "diagnoses": [],
        "procedures": []
    }
    
    # Convert text to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Iterate through medical terms and find matches
    for _, row in medical_terms_df.iterrows():
        term = row['Term'].lower()
        if term in text_lower:
            category = row['Category'].lower()
            if 'lab' in category:
                result['lab_tests'].append({
                    'term': row['Term'],
                    'code': row['Code'],
                    'description': row['Description']
                })
            elif 'diagnosis' in category:
                result['diagnoses'].append({
                    'term': row['Term'],
                    'code': row['Code'],
                    'description': row['Description']
                })
            elif 'procedure' in category:
                result['procedures'].append({
                    'term': row['Term'],
                    'code': row['Code'],
                    'description': row['Description']
                })
    
    return result

def convert_to_wav(input_path: str) -> str:
    """Convert audio file to WAV format."""
    try:
        # Create a temporary file for the WAV output
        output_path = str(Path(input_path).with_suffix('.wav'))
        
        # Read the audio file
        data, samplerate = sf.read(input_path)
        
        # Convert to mono if stereo
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
        
        # Resample to 16kHz if needed
        if samplerate != 16000:
            samples = len(data)
            new_samples = int(samples * 16000 / samplerate)
            data = signal.resample(data, new_samples)
            samplerate = 16000
        
        # Save as 16-bit PCM WAV
        sf.write(output_path, data, samplerate, subtype='PCM_16')
        
        return output_path
    except Exception as e:
        logger.error(f"Error converting audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error converting audio: {str(e)}")

def transcribe_audio(audio_file_path: str) -> str:
    """Transcribe audio file using Azure Speech-to-Text."""
    try:
        # Get Azure credentials from environment variables
        speech_key = os.getenv("AZURE_SPEECH_KEY")
        service_region = os.getenv("AZURE_SPEECH_REGION")
        
        logger.info(f"Using Azure region: {service_region}")
        
        if not speech_key or not service_region:
            raise HTTPException(status_code=500, detail="Azure Speech Services credentials not configured")
        
        # Configure speech service
        speech_config = speechsdk.SpeechConfig(
            subscription=speech_key,
            region=service_region
        )
        
        # Set audio format for WAV
        speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "5000")
        speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "1000")
        
        # Create audio config with specific format
        audio_config = speechsdk.audio.AudioConfig(filename=audio_file_path)
        
        # Create speech recognizer
        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config
        )
        
        logger.info("Starting speech recognition...")
        # Start recognition
        result = speech_recognizer.recognize_once()
        
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            logger.info("Speech recognition successful")
            return result.text
        else:
            error_details = f"Could not transcribe audio. Reason: {result.reason}"
            if result.reason == speechsdk.ResultReason.NoMatch:
                error_details += f", NoMatchDetails: {result.no_match_details}"
            logger.error(error_details)
            raise HTTPException(status_code=400, detail=error_details)
            
    except Exception as e:
        logger.error(f"Speech recognition error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Speech recognition error: {str(e)}")

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio_file(file: UploadFile = File(...)):
    """Endpoint to transcribe audio file and extract medical terms."""
    try:
        logger.info(f"Received file: {file.filename}")
        
        # Validate file type
        if not file.filename.lower().endswith('.wav'):
            raise HTTPException(status_code=400, detail="Only WAV files are supported")

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
            logger.info(f"Saved temporary file to: {temp_file_path}")
        
        try:
            # Convert to WAV with specific format
            logger.info("Converting to WAV format...")
            wav_path = convert_to_wav(temp_file_path)
            logger.info(f"Converted to WAV: {wav_path}")
            
            # Verify Azure credentials before transcription
            speech_key = os.getenv("AZURE_SPEECH_KEY")
            service_region = os.getenv("AZURE_SPEECH_REGION")
            
            if not speech_key or not service_region:
                logger.error("Azure credentials not found in environment variables")
                raise HTTPException(
                    status_code=500,
                    detail="Azure Speech Services credentials not configured. Please check your .env file."
                )
            
            logger.info("Starting audio transcription...")
            # Transcribe audio
            transcribed_text = transcribe_audio(wav_path)
            if not transcribed_text:
                raise HTTPException(status_code=400, detail="No speech detected in the audio file")
                
            logger.info(f"Transcription successful: {transcribed_text[:100]}...")
            
            # Match medical terms
            structured_data = match_medical_terms(transcribed_text)
            logger.info(f"Found {len(structured_data['lab_tests'])} lab tests, "
                       f"{len(structured_data['diagnoses'])} diagnoses, "
                       f"{len(structured_data['procedures'])} procedures")
            
            return TranscriptionResponse(
                text=transcribed_text,
                structured_data=structured_data
            )
        finally:
            # Clean up temporary files
            try:
                os.unlink(temp_file_path)
                if 'wav_path' in locals() and wav_path != temp_file_path:
                    os.unlink(wav_path)
                logger.info("Temporary files cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up temporary files: {str(e)}")
        
    except HTTPException as he:
        logger.error(f"HTTP Exception: {str(he)}")
        raise he
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")

@app.get("/medical-terms")
async def get_medical_terms():
    """Endpoint to get all medical terms."""
    return medical_terms_df.to_dict(orient='records')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 