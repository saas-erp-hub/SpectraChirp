from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response  # Changed from FileResponse
from pydantic import BaseModel
import numpy as np
import soundfile as sf
import logging
import os
import io  # Added for in-memory file handling
from .modem_mfsk import send_text_mfsk, receive_text_mfsk

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

app = FastAPI()

# Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    text: str
    mode: str


@app.post("/generate_signal")
def generate_signal(message: Message):
    """Generates an MFSK audio signal from text and returns it from memory."""
    try:
        # This function now returns an in-memory buffer
        audio_buffer = send_text_mfsk(message.text, mode=message.mode)
        
        # Return the audio data directly from the buffer
        return Response(
            content=audio_buffer.read(),
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=generated_signal.wav"},
        )
    except Exception as e:
        logging.exception("Error in generate_signal endpoint")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/decode_signal")
async def decode_signal(file: UploadFile = File(...)):
    """Decodes an MFSK audio signal from an uploaded WAV file in memory."""
    try:
        # Read the uploaded file into an in-memory buffer
        audio_bytes = await file.read()
        buffer = io.BytesIO(audio_bytes)
        buffer.seek(0)

        audio_data, _ = sf.read(buffer)
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

# Serve all static files from the frontend directory, including index.html at the root
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")

