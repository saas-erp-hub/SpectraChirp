from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import numpy as np
import soundfile as sf
import logging
import os
from scipy.io import wavfile
from .modem_mfsk import send_text_mfsk, receive_text_mfsk

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

app = FastAPI()

# Allow all origins for development, but you might want to restrict this in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    text: str
    mode: str  # e.g., 'DEFAULT', 'ROBUST'


@app.post("/generate_signal")
def generate_signal(message: Message):
    """Generates an MFSK audio signal from text input."""
    try:
        signal, _ = send_text_mfsk(message.text, mode=message.mode)
        file_path = "temp_audio.wav"
        sf.write(file_path, signal, 16000)  # Use a common sample rate
        return FileResponse(
            file_path, media_type="audio/wav", filename="generated_signal.wav"
        )
    except Exception as e:
        logging.exception("Error in generate_signal endpoint")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/decode_signal")
async def decode_signal(file: UploadFile = File(...)):
    """Decodes an MFSK audio signal from an uploaded WAV file."""
    try:
        temp_file_path = "temp_received_audio.wav"
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await file.read())

        audio_data, _ = sf.read(temp_file_path)
        decoded_text, _, _, detected_mode = receive_text_mfsk(audio_data)

        return {"decoded_text": decoded_text, "detected_mode": detected_mode}
    except Exception as e:
        logging.exception("Error in decode_signal endpoint")
        raise HTTPException(status_code=500, detail=str(e))


# --- Static Files Hosting ---
# This part serves the frontend files.
# It must be after all the API routes.

# Get the absolute path to the directory containing main.py
backend_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the path to the frontend directory
frontend_dir = os.path.join(backend_dir, '..', 'frontend')

# Mount the 'docs/images' directory to serve images for the README
images_dir = os.path.join(backend_dir, '..', 'docs', 'images')
app.mount("/docs/images", StaticFiles(directory=images_dir), name="images")

# Serve the main index.html at the root
@app.get("/")
async def read_index():
    index_path = os.path.join(frontend_dir, 'index.html')
    return FileResponse(index_path)

# Serve any other static files from the frontend directory
app.mount("/", StaticFiles(directory=frontend_dir), name="static")

