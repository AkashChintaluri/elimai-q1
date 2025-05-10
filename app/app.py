from flask import Flask, request, jsonify, send_from_directory
import azure.cognitiveservices.speech as speechsdk
import pandas as pd
import os
from pathlib import Path
from dotenv import load_dotenv
import logging
import soundfile as sf
import numpy as np
from scipy import signal
from scipy.io import wavfile
import json
from datetime import datetime
import tempfile

# Set up logging - helps us track what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Grab our Azure credentials from .env file
env_path = Path(__file__).parent / '.env'
logger.info(f"Looking for .env file at: {env_path}")
load_dotenv(dotenv_path=env_path)

# Double check we have our Azure keys
speech_key = os.getenv("AZURE_SPEECH_KEY")
service_region = os.getenv("AZURE_SPEECH_REGION")

if not speech_key or not service_region:
    raise ValueError("Azure Speech credentials not found. Please check your .env file.")

logger.info(f"Got speech key? {'Yes' if speech_key else 'No'}")
logger.info(f"Got service region? {'Yes' if service_region else 'No'}")

app = Flask(__name__)

# Load up our medical terms from CSV
MEDICAL_TERMS_PATH = Path(__file__).parent / "data" / "medical_terms.csv"
medical_terms_df = pd.read_csv(MEDICAL_TERMS_PATH)

# Make sure we have a place to store uploads
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOADS_DIR, exist_ok=True)

def load_medical_terms():
    """Grab all the medical terms from our CSV file"""
    try:
        terms_file = os.path.join(os.path.dirname(__file__), 'data', 'medical_terms.csv')
        df = pd.read_csv(terms_file)
        # Map the CSV columns to our expected format
        terms = df.apply(lambda row: {
            'name': row['Term'],
            'code': row['Code'],
            'description': row['Description'],
            'category': row['Category'].lower().replace(' ', '_')
        }, axis=1).tolist()
        return terms
    except Exception as e:
        logger.error(f"Oops! Couldn't load medical terms: {str(e)}")
        return []

def save_medical_terms(df):
    """Save our medical terms back to the CSV file"""
    try:
        terms_file = os.path.join(os.path.dirname(__file__), 'data', 'medical_terms.csv')
        df.to_csv(terms_file, index=False)
        return True
    except Exception as e:
        logger.error(f"Uh oh, couldn't save medical terms: {str(e)}")
        return False

def convert_to_wav(audio_file):
    """Convert any audio file to WAV format that Azure can understand"""
    try:
        # Set up our temp files
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        
        # Save what the user uploaded
        audio_file.save(temp_input.name)
        temp_input.close()  # Close the file handle
        
        logger.info("Reading audio data")
        # Read the audio data
        data, samplerate = sf.read(temp_input.name)
        
        # If it's stereo, mix it down to mono
        if len(data.shape) > 1:
            logger.info("Converting stereo to mono")
            data = np.mean(data, axis=1)
        
        # Make sure it's 16kHz (Azure likes this)
        if samplerate != 16000:
            logger.info(f"Resampling from {samplerate}Hz to 16000Hz")
            samples = len(data)
            new_samples = int(samples * 16000 / samplerate)
            data = signal.resample(data, new_samples)
            samplerate = 16000
        
        # Convert to 16-bit PCM (Azure's favorite format)
        logger.info("Converting to 16-bit PCM")
        data = np.int16(data * 32767)
        
        # Save it as a WAV file
        logger.info("Saving as WAV file")
        sf.write(temp_output.name, data, samplerate, subtype='PCM_16')
        temp_output.close()  # Close the file handle
        
        # Clean up our temp input file
        if os.path.exists(temp_input.name):
            os.unlink(temp_input.name)
            logger.info("Cleaned up temporary input file")
        
        return temp_output.name
    except Exception as e:
        logger.error(f"Error in convert_to_wav: {str(e)}", exc_info=True)
        if 'temp_input' in locals() and os.path.exists(temp_input.name):
            os.unlink(temp_input.name)
        if 'temp_output' in locals() and os.path.exists(temp_output.name):
            os.unlink(temp_output.name)
        raise

def transcribe_audio(audio_file):
    """Send the audio to Azure and get back what was said"""
    temp_file = None
    wav_file = None
    try:
        # Handle MP3 files
        if audio_file.filename.lower().endswith('.mp3'):
            logger.info("Converting MP3 to WAV")
            wav_file = convert_to_wav(audio_file)
        else:
            # For WAV files, just save it temporarily
            logger.info("Saving WAV file temporarily")
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            audio_file.save(temp_file.name)
            temp_file.close()  # Close the file handle
            wav_file = temp_file.name

        logger.info(f"Using WAV file: {wav_file}")

        # Set up Azure with proper configuration
        try:
            speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
            speech_config.speech_recognition_language = "en-US"  # Set language explicitly
            speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "5000")
            speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "1000")
            
            # Configure audio settings
            audio_config = speechsdk.audio.AudioConfig(filename=wav_file)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config
            )
        except Exception as e:
            logger.error(f"Failed to configure Azure Speech SDK: {str(e)}", exc_info=True)
            raise ValueError("Failed to configure speech recognition. Please check Azure credentials.")

        logger.info("Starting speech recognition")
        # Do the actual transcription with proper error handling
        result = speech_recognizer.recognize_once_async().get()
        
        # Clean up our temp file
        if wav_file and os.path.exists(wav_file):
            try:
                os.unlink(wav_file)
                logger.info("Cleaned up temporary WAV file")
            except Exception as e:
                logger.warning(f"Could not delete temp file {wav_file}: {str(e)}")
        
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            logger.info(f"Speech recognized: {result.text}")
            return result.text
        elif result.reason == speechsdk.ResultReason.NoMatch:
            logger.error(f"No speech could be recognized: {result.no_match_details}")
            return None
        else:
            logger.error(f"Speech recognition failed: {result.reason}")
            return None
            
    except Exception as e:
        logger.error(f"Error in transcribe_audio: {str(e)}", exc_info=True)
        # Clean up temp files in case of error
        if wav_file and os.path.exists(wav_file):
            try:
                os.unlink(wav_file)
            except Exception as cleanup_error:
                logger.warning(f"Could not delete temp file {wav_file}: {str(cleanup_error)}")
        return None

def match_medical_terms(text, medical_terms):
    """Look through the text and find any medical terms we know about"""
    if not text:
        return {
            "lab_tests": [],
            "diagnoses": [],
            "procedures": [],
            "medications": [],
            "treatments": []
        }
    
    text = text.lower()
    matched_terms = {
        "lab_tests": [],
        "diagnoses": [],
        "procedures": [],
        "medications": [],
        "treatments": []
    }
    
    # Check each term we know about
    for term in medical_terms:
        term_name = term['name'].lower()
        if term_name in text:
            category = term['category']
            # Put it in the right category
            if category == 'lab_test':
                matched_terms['lab_tests'].append(term)
            elif category == 'diagnosis':
                matched_terms['diagnoses'].append(term)
            elif category == 'procedure':
                matched_terms['procedures'].append(term)
            elif category == 'medication':
                matched_terms['medications'].append(term)
            elif category == 'treatment':
                matched_terms['treatments'].append(term)
    
    return matched_terms

# Routes for serving our web pages
@app.route('/')
def index():
    """Show the main page"""
    return send_from_directory('static', 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve up our static files (JS, CSS, etc)"""
    return send_from_directory('static', path)

@app.route('/terms')
def terms_page():
    """Show the terms management page"""
    return send_from_directory('static', 'terms.html')

# API endpoints
@app.route('/api/terms', methods=['GET'])
def get_terms():
    """Get all the medical terms we know about"""
    try:
        terms = load_medical_terms()
        return jsonify({
            'status': 'success',
            'data': terms
        }), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        logger.error(f"Couldn't get the terms: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500, {'Content-Type': 'application/json'}

@app.route('/api/terms', methods=['POST'])
def add_term():
    """Add a new medical term to our list"""
    try:
        # Make sure they sent us JSON
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'message': 'Send us JSON, not something else'
            }), 400, {'Content-Type': 'application/json'}

        term = request.json
        required_fields = ['name', 'code', 'description', 'category']
        
        # Check they gave us everything we need
        for field in required_fields:
            if field not in term:
                return jsonify({
                    'status': 'error',
                    'message': f'Hey, you forgot to give us the {field}'
                }), 400, {'Content-Type': 'application/json'}
        
        # Make sure the category makes sense
        valid_categories = ['lab_test', 'diagnosis', 'procedure', 'medication', 'treatment']
        if term['category'] not in valid_categories:
            return jsonify({
                'status': 'error',
                'message': f'That category is no good. Try one of these: {", ".join(valid_categories)}'
            }), 400, {'Content-Type': 'application/json'}
        
        # Load up our existing terms
        terms = load_medical_terms()
        
        # Check if this code is already taken
        if term['code'] in [t['code'] for t in terms]:
            return jsonify({
                'status': 'error',
                'message': 'Oops, that code is already in use'
            }), 409, {'Content-Type': 'application/json'}
        
        # Add the new term
        terms.append(term)
        
        # Convert to DataFrame and save
        df = pd.DataFrame([{
            'Category': term['category'].replace('_', ' ').title(),
            'Term': term['name'],
            'Code': term['code'],
            'Description': term['description']
        } for term in terms])
        
        if save_medical_terms(df):
            return jsonify({
                'status': 'success',
                'message': 'Great! Added your new term',
                'data': term
            }), 201, {'Content-Type': 'application/json'}
        else:
            return jsonify({
                'status': 'error',
                'message': 'Hmm, something went wrong saving that'
            }), 500, {'Content-Type': 'application/json'}
            
    except Exception as e:
        logger.error(f"Something went wrong adding the term: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500, {'Content-Type': 'application/json'}

@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    """Take some audio, figure out what was said, and find any medical terms"""
    try:
        # Make sure they sent us an audio file
        if 'audio' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'Hey, where\'s the audio file?'
            }), 400, {'Content-Type': 'application/json'}
        
        audio_file = request.files['audio']
        if not audio_file.filename:
            return jsonify({
                'status': 'error',
                'message': 'You need to pick a file first'
            }), 400, {'Content-Type': 'application/json'}
        
        # Check if it's a file type we can handle
        if not audio_file.filename.lower().endswith(('.wav', '.mp3')):
            return jsonify({
                'status': 'error',
                'message': 'Sorry, we only do WAV and MP3 files'
            }), 400, {'Content-Type': 'application/json'}
        
        # Send it to Azure to figure out what was said
        transcription = transcribe_audio(audio_file)
        if not transcription:
            return jsonify({
                'status': 'error',
                'message': 'Hmm, we couldn\'t understand what was said'
            }), 500, {'Content-Type': 'application/json'}
        
        # Look for any medical terms in what was said
        medical_terms = load_medical_terms()
        matched_terms = match_medical_terms(transcription, medical_terms)
        
        # Put it all together
        response = {
            'status': 'success',
            'data': {
                'transcription': transcription,
                'medical_terms': matched_terms,
                'summary': {
                    'lab_tests': len(matched_terms["lab_tests"]),
                    'diagnoses': len(matched_terms["diagnoses"]),
                    'procedures': len(matched_terms["procedures"]),
                    'medications': len(matched_terms["medications"]),
                    'treatments': len(matched_terms["treatments"])
                }
            }
        }
        
        return jsonify(response), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        logger.error(f"Something went wrong with the transcription: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500, {'Content-Type': 'application/json'}

if __name__ == '__main__':
    # Start the server
    app.run(debug=True, port=5000) 