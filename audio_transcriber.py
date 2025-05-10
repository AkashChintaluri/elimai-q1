import tkinter as tk
from tkinter import filedialog, messagebox
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import azure.cognitiveservices.speech as speechsdk
import os
import tempfile
from datetime import datetime
import time
from config import AZURE_SPEECH_KEY, AZURE_SPEECH_REGION

class AudioTranscriber:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Audio Transcriber")
        self.root.geometry("400x300")
        
        # Azure Speech Service configuration
        self.speech_key = AZURE_SPEECH_KEY
        self.service_region = AZURE_SPEECH_REGION
        
        if not self.speech_key or not self.service_region or self.speech_key == "your-speech-key-here":
            messagebox.showerror("Error", "Please configure your Azure Speech Services credentials in config.py")
            self.root.destroy()
            return
        
        self.setup_ui()
        
    def setup_ui(self):
        # Create buttons
        self.select_file_btn = tk.Button(
            self.root,
            text="Select Audio File",
            command=self.select_audio_file,
            width=20,
            height=2
        )
        self.select_file_btn.pack(pady=20)
        
        self.record_btn = tk.Button(
            self.root,
            text="Record Audio",
            command=self.toggle_recording,
            width=20,
            height=2
        )
        self.record_btn.pack(pady=20)
        
        self.status_label = tk.Label(self.root, text="")
        self.status_label.pack(pady=20)
        
        self.transcription_text = tk.Text(self.root, height=5, width=40)
        self.transcription_text.pack(pady=20)
        
        self.is_recording = False
        self.recording = []
        
    def select_audio_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.wav *.mp3")]
        )
        if file_path:
            self.transcribe_audio_file(file_path)
    
    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        self.is_recording = True
        self.recording = []
        self.record_btn.config(text="Stop Recording")
        self.status_label.config(text="Recording...")
        
        def callback(indata, frames, time, status):
            if status:
                print(status)
            self.recording.append(indata.copy())
        
        self.stream = sd.InputStream(
            channels=1,
            samplerate=16000,
            callback=callback
        )
        self.stream.start()
    
    def stop_recording(self):
        self.is_recording = False
        self.record_btn.config(text="Record Audio")
        self.status_label.config(text="Processing...")
        
        self.stream.stop()
        self.stream.close()
        
        # Save recording to temporary file
        recording_data = np.concatenate(self.recording, axis=0)
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_file_path = temp_file.name
        temp_file.close()  # Close the file handle
        
        wav.write(temp_file_path, 16000, recording_data)
        
        # Transcribe the audio
        self.transcribe_audio_file(temp_file_path)
        
        # Wait a bit before trying to delete the file
        time.sleep(1)
        try:
            os.unlink(temp_file_path)
        except PermissionError:
            # If we can't delete it now, it will be cleaned up by the system later
            pass
    
    def transcribe_audio_file(self, audio_file_path):
        try:
            # Configure speech service
            speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key,
                region=self.service_region
            )
            audio_config = speechsdk.audio.AudioConfig(filename=audio_file_path)
            
            # Create speech recognizer
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config
            )
            
            # Start recognition
            self.status_label.config(text="Transcribing...")
            result = speech_recognizer.recognize_once()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                self.transcription_text.delete(1.0, tk.END)
                self.transcription_text.insert(tk.END, result.text)
                self.status_label.config(text="Transcription complete")
            else:
                self.status_label.config(text="Transcription failed")
                messagebox.showerror("Error", "Could not transcribe audio")
                
        except Exception as e:
            self.status_label.config(text="Error occurred")
            messagebox.showerror("Error", str(e))
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = AudioTranscriber()
    app.run() 