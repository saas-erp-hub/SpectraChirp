import numpy as np
import pytest

import soundfile as sf
from backend.modem_mfsk import send_text_mfsk, receive_text_mfsk
from backend.config import SAMPLE_RATE, RSC


def calculate_bit_error_rate(original_bits: str, received_bits: str) -> float:
    """Calculates the bit error rate (BER) between two bit strings."""
    if not original_bits:
        return 0.0

    # Pad received_bits to match original_bits length for comparison
    padded_received_bits = received_bits.ljust(len(original_bits), "0")

    errors = sum(
        1
        for i in range(len(original_bits))
        if original_bits[i] != padded_received_bits[i]
    )
    return errors / len(original_bits)


@pytest.mark.parametrize(
    "message",
    [
        "Hello World!",
        "This is a longer test message to check multi-packet transmission.",
        "Short",
    ],
)
def test_packet_loopback(message):
    """Tests the entire send and receive process under ideal (noiseless) conditions."""
    sent_signal_buffer = send_text_mfsk(message)

    # The receiver expects a numpy array, so we read the buffer back
    sent_signal_buffer.seek(0)
    sent_signal, r_samplerate = sf.read(sent_signal_buffer)
    assert r_samplerate == SAMPLE_RATE

    received_text, _, _, _ = receive_text_mfsk(sent_signal)
    assert received_text == message


@pytest.mark.parametrize(
    "message",
    [
        "Hello World!",
        "This is a longer test message to check multi-packet transmission.",
        "Short",
    ],
)
def test_mfsk_loopback_with_noise(message):
    """Tests the MFSK modem loopback with noise and checks the decoding."""
    sent_signal_buffer = send_text_mfsk(message)

    # Read the buffer into a numpy array to add noise
    sent_signal_buffer.seek(0)
    sent_signal, r_samplerate = sf.read(sent_signal_buffer)
    assert r_samplerate == SAMPLE_RATE

    # Add some noise to the signal
    snr_db = 10  # Example Signal-to-Noise Ratio
    signal_power = np.mean(sent_signal**2)
    noise_power = signal_power / (10 ** (snr_db / 10))
    noise = np.random.normal(0, np.sqrt(noise_power), sent_signal.shape)
    noisy_signal = sent_signal + noise

    received_text, _, _, _ = receive_text_mfsk(noisy_signal)
    assert received_text == message


def test_reedsolomon_correction():
    """Testet die Reed-Solomon-Fehlerkorrektur direkt."""
    original_data = b"Hello World! This is a test message for Reed-Solomon."

    # Encode the original data
    encoded_data = RSC.encode(original_data)

    # Introduce a single byte error
    corrupted_data = bytearray(encoded_data)
    if len(corrupted_data) > 0:
        corrupted_data[0] ^= 0x01  # Flip a bit in the first byte
    else:
        pytest.fail("Encoded data too short for corruption.")

    # Decode the corrupted data
    try:
        decoded_data, _, _ = RSC.decode(bytes(corrupted_data))
        assert decoded_data == original_data
    except Exception as e:
        pytest.fail(f"Reed-Solomon decoding failed for single byte error: {e}")

    # Introduce multiple errors (exceeding correction capability)
    too_corrupted_data = bytearray(encoded_data)
    for i in range(
        min(len(too_corrupted_data), RSC.nsym + 1)
    ):  # Mehr Fehler als korrigierbar
        too_corrupted_data[i] ^= 0x01

    # Expect decoding to fail
    with pytest.raises(
        Exception
    ):  # RSC.decode wirft eine Ausnahme bei unkorrigierbaren Fehlern
        RSC.decode(bytes(too_corrupted_data))
