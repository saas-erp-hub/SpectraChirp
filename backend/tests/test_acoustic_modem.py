import numpy as np
import pytest
import soundfile as sf
from backend.modem_mfsk import send_text_mfsk, receive_text_mfsk
from backend.config import SAMPLE_RATE

# --- Test helper functions to simulate channel distortions ---

def _simulate_clipping(signal, threshold=0.8):
    """Simulates hard-clipping when the signal exceeds a threshold."""
    return np.clip(signal, -threshold, threshold)

def _simulate_time_offset(signal, offset_seconds):
    """Simulates a delayed recording by slicing the beginning of the signal."""
    offset_samples = int(offset_seconds * SAMPLE_RATE)
    if offset_samples >= signal.shape[0]:
        return np.array([]) # Return empty signal if offset is too large
    return signal[offset_samples:]

def _add_noise(signal, snr_db):
    """Adds Gaussian noise to the signal to achieve a specific SNR."""
    signal_power = np.mean(np.abs(signal)**2)
    if signal_power == 0:
        return signal
    noise_power = signal_power / (10**(snr_db / 10))
    noise = np.random.normal(0, np.sqrt(noise_power), signal.shape)
    return signal + noise

# --- Test Cases ---

def test_perfect_loopback():
    """Tests the transmission under ideal (loopback) conditions."""
    test_message = "This is a perfect loopback test."
    buffer = send_text_mfsk(test_message)
    buffer.seek(0)
    sent_signal, _ = sf.read(buffer)
    received_text, _, _, _ = receive_text_mfsk(sent_signal)
    assert received_text.strip() == test_message

@pytest.mark.parametrize("snr_db", [20, 15, 10])
def test_with_noise(snr_db):
    """Tests robustness against different levels of noise."""
    test_message = "Testing with noise."
    buffer = send_text_mfsk(test_message)
    buffer.seek(0)
    sent_signal, _ = sf.read(buffer)
    noisy_signal = _add_noise(sent_signal, snr_db)
    received_text, _, _, _ = receive_text_mfsk(noisy_signal)
    assert received_text.strip() == test_message

def test_with_clipping():
    """Tests robustness against signal clipping."""
    test_message = "Testing with signal clipping."
    buffer = send_text_mfsk(test_message)
    buffer.seek(0)
    sent_signal, _ = sf.read(buffer)
    clipped_signal = _simulate_clipping(sent_signal, threshold=0.7)
    received_text, _, _, _ = receive_text_mfsk(clipped_signal)
    assert received_text.strip() == test_message

@pytest.mark.parametrize("offset_sec", [0.01, 0.02])
def test_with_time_offset(offset_sec):
    """
    Tests robustness against a delayed recording.
    Since there is sync, the message should still be detected.
    """
    test_message = "A long message to test robustness against time offsets."
    buffer = send_text_mfsk(test_message)
    buffer.seek(0)
    sent_signal, _ = sf.read(buffer)
    offset_signal = _simulate_time_offset(sent_signal, offset_sec)
    received_text, _, _, _ = receive_text_mfsk(offset_signal)
    assert len(received_text) > 0
    # The received text might be slightly different due to the offset, but should contain the core message
    assert "message" in received_text

def test_with_all_distortions():
    """Tests robustness against a combination of all distortions."""
    test_message = "Final boss: a long message with all distortions combined."
    buffer = send_text_mfsk(test_message)
    buffer.seek(0)
    sent_signal, _ = sf.read(buffer)
    distorted_signal = _simulate_clipping(sent_signal, threshold=0.8)
    distorted_signal = _add_noise(distorted_signal, snr_db=18)
    distorted_signal = _simulate_time_offset(distorted_signal, offset_seconds=0.015)
    received_text, _, _, _ = receive_text_mfsk(distorted_signal)
    assert "message" in received_text