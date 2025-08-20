from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response  # Changed from FileResponse
from pydantic import BaseModel
import soundfile as sf
import logging
import os
import io  # Added for in-memory file handling
from pydub import AudioSegment
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
            headers={
                "Content-Disposition": "attachment; filename=generated_signal.wav"
            },
        )
    except Exception as e:
        logging.exception("Error in generate_signal endpoint")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/decode_signal")
async def decode_signal(file: UploadFile = File(...)):
    """Decodes an MFSK audio signal from an uploaded audio file in memory,
    converting it to WAV if necessary."""
    try:
        audio_bytes = await file.read()
        input_buffer = io.BytesIO(audio_bytes)
        input_buffer.seek(0)

        # Try to read directly with soundfile if it's a WAV, otherwise use pydub for conversion
        if file.content_type == "audio/wav":
            audio_data, _ = sf.read(input_buffer)
        else:
            # Determine input format based on content type or filename
            input_format = file.content_type.split('/')[-1] if file.content_type else None
            if not input_format and file.filename:
                input_format = file.filename.split('.')[-1]
            
            # Fallback for unknown or generic types
            if input_format not in ['wav', 'mp3', 'ogg', 'flac', 'webm']:
                input_format = None # Let pydub try to guess or raise error

            audio_segment = AudioSegment.from_file(input_buffer)

            # Export to WAV format in memory for soundfile to read
            wav_buffer = io.BytesIO()
            audio_segment.export(wav_buffer, format="wav")
            wav_buffer.seek(0)

            audio_data, _ = sf.read(wav_buffer)

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
frontend_dir = os.path.join(backend_dir, "..", "frontend")

# Mount the 'docs/images' directory to serve images for the README
images_dir = os.path.join(backend_dir, "..", "docs", "images")
app.mount("/docs/images", StaticFiles(directory=images_dir), name="images")

# Serve all static files from the frontend directory, including index.html at the root
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")
