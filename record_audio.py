import sounddevice as sd
import soundfile as sf
import numpy as np
import keyboard
import os
from datetime import datetime
from pathlib import Path

def record_audio(output_dir="recordings", duration=None):
    """
    Record audio from microphone and save as WAV file.
    
    Args:
        output_dir (str): Directory to save recordings
        duration (int): Duration in seconds. If None, recording continues until 'q' is pressed
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Audio recording parameters
    CHANNELS = 1
    RATE = 16000  # 16kHz sample rate
    DTYPE = np.int16  # 16-bit PCM
    
    print("* Recording started")
    print("Press 'q' to stop recording...")
    
    try:
        if duration:
            # Record for specified duration
            recording = sd.rec(
                int(duration * RATE),
                samplerate=RATE,
                channels=CHANNELS,
                dtype=DTYPE
            )
            sd.wait()  # Wait until recording is finished
        else:
            # Record until 'q' is pressed
            recording = []
            def callback(indata, frames, time, status):
                if status:
                    print(status)
                recording.append(indata.copy())
            
            with sd.InputStream(
                samplerate=RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                callback=callback
            ):
                while True:
                    if keyboard.is_pressed('q'):
                        break
                    sd.sleep(100)  # Sleep to prevent high CPU usage
            
            recording = np.concatenate(recording, axis=0)
        
        if len(recording) > 0:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.wav"
            filepath = output_path / filename
            
            # Save the recorded audio
            sf.write(str(filepath), recording, RATE)
            print(f"* Recording saved to: {filepath}")
        else:
            print("* No audio recorded")
            
    except KeyboardInterrupt:
        print("\n* Recording interrupted")
    except Exception as e:
        print(f"* Error during recording: {str(e)}")

def main():
    print("Audio Recording Tool")
    print("-------------------")
    print("1. Press Enter to start recording")
    print("2. Press 'q' to stop recording")
    print("3. Recordings will be saved in the 'recordings' directory")
    print("\nPress Enter to start...")
    
    input()  # Wait for Enter key
    
    # Record audio (press 'q' to stop)
    record_audio()

if __name__ == "__main__":
    main() 