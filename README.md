# Medical Dictation System

A web-based application that converts voice dictations into structured medical data using Azure's Speech-to-Text API. The system is designed to handle medical terminology and provide accurate transcriptions with proper formatting.

## Features

- Real-time audio recording with optimized settings
- Support for WAV audio format (required by Azure Speech Services)
- Automatic medical term matching and categorization
- Combined transcription display with deduplicated medical terms
- Error handling for various scenarios:
  - No speech detected
  - Initial silence timeout
  - Audio format issues
  - Server errors
  - Network connectivity issues

## Prerequisites

- Python 3.8 or higher
- Azure Speech Services account and API key
- Modern web browser with microphone access
- Required Python packages (see requirements.txt)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/AkashChintaluri/elimai-q1
cd elimai-q1
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Set up your Azure Speech Services credentials:
   - Create a `.env` file in the project root
   - Add your Azure Speech Services key and region:
```
AZURE_SPEECH_KEY=your_key_here
AZURE_SPEECH_REGION=your_region_here
```

## Usage

1. Start the Hypercorn server:
```bash
cd app
hypercorn app.app:app --bind 0.0.0.0:5000
```

2. Open your web browser and navigate to `http://localhost:5000`

3. Use the interface to:
   - Record audio using the microphone
   - Upload existing audio files
   - View transcriptions and matched medical terms
   - Toggle between pretty and raw output formats

## Audio Requirements

- Format: WAV (16-bit PCM)
- Sample Rate: 16000 Hz
- Channels: Mono
- Bit Depth: 16-bit

## Error Handling

The system handles various error scenarios:

- **No Speech Detected**: When the audio contains no speech or is too quiet
- **Initial Silence**: When there's too much silence at the start of the recording
- **Format Issues**: When the audio format is incompatible
- **Server Errors**: When the Azure Speech Services API encounters issues
- **Network Issues**: When there are connectivity problems

## Development

The project uses:
- Quart (ASGI framework) for the backend
- Hypercorn as the ASGI server
- Azure Speech Services for speech recognition
- Web Audio API for client-side audio processing
- Modern JavaScript for frontend functionality

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request