# Audio Transcriber

A simple Python application that allows you to transcribe audio using Azure Speech Services. You can either select an audio file or record audio directly through the application.

## Prerequisites

- Python 3.7 or higher
- Azure Speech Services subscription
- Windows operating system (for the file browser)

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your Azure Speech Services credentials:
   - Open `config.py`
   - Replace `your-speech-key-here` with your Azure Speech Services key
   - Replace `your-region-here` with your Azure Speech Services region (e.g., "eastus", "westeurope")

## Usage

1. Run the application:
```bash
python audio_transcriber.py
```

2. The application provides two options:
   - "Select Audio File": Opens a file browser to select an audio file (.wav or .mp3)
   - "Record Audio": Records audio from your microphone

3. After selecting a file or recording audio, the transcription will appear in the text box below.

## Features

- Simple GUI interface
- Support for both file selection and direct recording
- Real-time status updates
- Error handling and user feedback
- Supports WAV and MP3 audio files
- Easy configuration through config.py

## Note

Make sure your microphone is properly configured and accessible before using the recording feature. 