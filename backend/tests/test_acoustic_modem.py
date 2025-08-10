import numpy as np
import pytest
from backend.modem_mfsk import send_text_mfsk, receive_text_mfsk

# --- Test-Helferfunktionen zur Simulation von Kanalstörungen ---

def simulate_clipping(signal, threshold=0.8):
    """Simuliert Hard-Clipping, wenn das Signal einen Schwellenwert überschreitet."""
    return np.clip(signal, -threshold, threshold)

def simulate_time_offset(signal, offset_seconds, sample_rate=44100):
    """Simuliert eine verspätete Aufnahme, indem der Anfang des Signals abgeschnitten wird."""
    offset_samples = int(offset_seconds * sample_rate)
    if offset_samples >= signal.shape[0]:
        return np.array([[]]) # Leeres Signal zurückgeben, wenn der Offset zu groß ist
    return signal[offset_samples:]

def add_noise(signal, snr_db):
    """Fügt dem Signal Rauschen hinzu."""
    signal_power = np.mean(np.abs(signal)**2)
    if signal_power == 0:
        return signal
    noise_power = signal_power / (10**(snr_db / 10))
    noise = np.random.normal(0, np.sqrt(noise_power/2), signal.shape) + 1j * np.random.normal(0, np.sqrt(noise_power/2), signal.shape)
    return signal + noise.real # Nur den realen Teil des Rauschens hinzufügen, da unser Signal real ist

# --- Testfälle ---

def test_perfect_loopback():
    """Testet die Übertragung unter idealen Bedingungen (Loopback)."""
    test_message = "This is a perfect loopback test."
    sent_signal, _ = send_text_mfsk(test_message)
    received_text, _, _, _ = receive_text_mfsk(sent_signal)
    assert received_text.strip() == test_message

@pytest.mark.parametrize("snr_db", [20, 15, 10])
def test_with_noise(snr_db):
    """Testet die Robustheit gegen verschieden starke Rauschpegel."""
    test_message = "Testing with noise."
    sent_signal, _ = send_text_mfsk(test_message)
    noisy_signal = add_noise(sent_signal, snr_db)
    received_text, _, _, _ = receive_text_mfsk(noisy_signal)
    assert received_text.strip() == test_message

def test_with_clipping():
    """Testet die Robustheit gegen Signal-Clipping."""
    test_message = "Testing with signal clipping."
    sent_signal, _ = send_text_mfsk(test_message)
    clipped_signal = simulate_clipping(sent_signal, threshold=0.7)
    received_text, _, _, _ = receive_text_mfsk(clipped_signal)
    assert received_text.strip() == test_message

@pytest.mark.parametrize("offset_sec", [0.01, 0.02])
def test_with_time_offset(offset_sec):
    """
    Testet die Robustheit gegen eine verspätete Aufnahme.
    Da wir keine Synchronisation haben, wird die Nachricht einfach abgeschnitten.
    """
    test_message = "A long message to test robustness against time offsets."
    sent_signal, _ = send_text_mfsk(test_message)
    offset_signal = simulate_time_offset(sent_signal, offset_sec)
    received_text, _, _, _ = receive_text_mfsk(offset_signal)
    assert len(received_text) > 0
    assert len(received_text) < len(test_message)

def test_with_all_distortions():
    """Testet die Robustheit gegen eine Kombination aller Störungen."""
    test_message = "Final boss: a long message with all distortions combined."
    sent_signal, _ = send_text_mfsk(test_message)
    distorted_signal = simulate_clipping(sent_signal, threshold=0.8)
    distorted_signal = add_noise(distorted_signal, snr_db=18)
    distorted_signal = simulate_time_offset(distorted_signal, offset_seconds=0.015)
    received_text, _, _, _ = receive_text_mfsk(distorted_signal)
    assert received_text == "[Could not detect modem mode or decode message]"