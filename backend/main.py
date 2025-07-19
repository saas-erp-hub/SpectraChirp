from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import numpy as np
import soundfile as sf
import logging
from scipy.io import wavfile
from .modem_mfsk import send_text_mfsk, receive_text_mfsk

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

app = FastAPI()

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
    """Generates an MFSK audio signal from text input.

    Args:
        message: A Message object containing the text to encode and the modem mode.

    Returns:
        A FileResponse containing the generated audio signal as a WAV file.
    """
    try:
        
        result = send_text_mfsk(
            message.text, mode=message.mode
        )
        print(f"DEBUG: generate_signal received {len(result)} values")
        signal, all_full_packet_bytes = result

        file_path = "temp_audio.wav"
        # Use a sample rate of 16000 and no subtype for browser compatibility
        sf.write(file_path, signal, 16000)
        return FileResponse(
            file_path, media_type="audio/wav", filename="generated_signal.wav"
        )
    except Exception as e:
        logging.exception("Error in generate_signal endpoint")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/decode_signal")
async def decode_signal(file: UploadFile = File(...)):
    """Decodes an MFSK audio signal from an uploaded WAV file.

    Args:
        file: The uploaded WAV file containing the audio signal.

    Returns:
        A dictionary containing the decoded text message.
    """
    logging.info(f"Received decode request for modem: mfsk")
    try:
        temp_file_path = "temp_received_audio.wav"
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await file.read())
        logging.info(f"Saved uploaded file to: {temp_file_path}")

        try:
            audio_data, sample_rate = sf.read(temp_file_path)
            logging.info(
                f"Read audio with soundfile. Shape: {audio_data.shape}, Sample Rate: {sample_rate}"
            )
        except Exception:
            logging.warning("Failed to read with soundfile, trying scipy.io.wavfile.")
            sample_rate, audio_data = wavfile.read(temp_file_path)
            if audio_data.dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32767.0
            elif audio_data.dtype == np.int32:
                audio_data = audio_data.astype(np.float32) / 2147483647.0

        if audio_data.ndim == 1:
            audio_data = np.column_stack((audio_data, audio_data))

        decoded_text = ""
        decoded_text, original_bits, encoded_bits, detected_mode = receive_text_mfsk(
            audio_data
        )

        logging.info(f"Decoded text: {decoded_text}")
        return {"decoded_text": decoded_text, "detected_mode": detected_mode}
    except Exception as e:
        logging.exception("Error in decode_signal endpoint")
        raise HTTPException(status_code=500, detail=str(e))
