# Medical Dictation System

A backend system that converts doctor voice dictations into structured medical data using Azure's Speech-to-Text API. The system transcribes audio input and maps the results to predefined medical terms and services.

## Features

- Real-time audio recording and file upload support
- Azure Speech-to-Text integration for accurate transcription
- Medical term matching against a predefined database
- Structured JSON output for EMR system integration
- Simple web interface for testing
- RESTful API endpoints

## Prerequisites

- Python 3.7 or higher
- Azure Speech Services subscription
- Modern web browser (for the UI demo)

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd medical-dictation-system
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure Azure Speech Services:
   - Create a `.env` file in the project root
   - Add your Azure credentials:
   ```
   AZURE_SPEECH_KEY=your-speech-key
   AZURE_SPEECH_REGION=your-region
   ```

## Running the Application

1. Start the backend server:
```bash
cd app
uvicorn main:app --reload
```

2. Open the web interface:
   - Navigate to `http://localhost:8000/static/index.html` in your browser

## API Endpoints

### POST /transcribe
Transcribes audio and extracts medical terms.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: audio file (WAV or MP3)

**Response:**
```json
{
    "text": "transcribed text",
    "structured_data": {
        "lab_tests": [
            {
                "term": "CBC",
                "code": "LAB001",
                "description": "Complete Blood Count"
            }
        ],
        "diagnoses": [],
        "procedures": []
    }
}
```

### GET /medical-terms
Returns all medical terms from the database.

## Testing with Postman

1. Open Postman
2. Create a new POST request to `http://localhost:8000/transcribe`
3. Set the request type to `form-data`
4. Add a key named `file` and select a WAV or MP3 file
5. Send the request

## Project Structure

```
medical-dictation-system/
├── app/
│   ├── main.py              # FastAPI application
│   └── static/
│       └── index.html       # Web interface
├── data/
│   └── medical_terms.xlsx   # Medical terms database
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Error Handling

The system includes comprehensive error handling for:
- Invalid audio files
- Azure Speech Services errors
- Missing medical term matches
- API request validation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 