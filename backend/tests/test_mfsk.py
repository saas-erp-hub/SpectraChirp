import numpy as np
import pytest
import matplotlib.pyplot as plt
import itertools
from itertools import combinations
from backend.modem_mfsk import send_text_mfsk, receive_text_mfsk, _bytes_to_signal, generate_chirp_signal, PACKET_CRC_SIZE, SAMPLE_RATE, bits_to_bytes, MODEM_MODES, RSC

def calculate_ber(original_bits: str, received_bits: str) -> float:
    """Berechnet die Bitfehlerrate zwischen zwei Bit-Strings."""
    if not original_bits:
        return 0.0
    
    # Pad received_bits to match original_bits length for comparison
    padded_received_bits = received_bits.ljust(len(original_bits), '0')
    
    errors = sum(1 for i in range(len(original_bits)) if original_bits[i] != padded_received_bits[i])
    return errors / len(original_bits)

@pytest.mark.parametrize("message", [
    "Hello World!",
    "This is a longer test message to check multi-packet transmission.",
    "Short"
])
def test_packet_loopback(message):
    """Testet den gesamten Sende- und Empfangsvorgang mit Paketstruktur unter idealen Bedingungen."""
    sent_signal, all_full_packet_bytes = send_text_mfsk(message)
    received_text, demod_bits_str, decoded_content_bits_str, _ = receive_text_mfsk(sent_signal)
    assert received_text == message

    # Optional: Überprüfen der BER im Idealfall (sollte 0 sein)
    # Um original_bits zu erhalten, müssen wir die Daten vor der Kodierung extrahieren
    original_bits_list = []
    for packet_bytes in all_full_packet_bytes:
        # Extrahiere den ursprünglichen Paketinhalt (Header + Payload) vor der LDPC-Kodierung und CRC
        # Dies erfordert eine Anpassung, da all_full_packet_bytes bereits kodierte Daten enthält
        # Für diesen Test nehmen wir an, dass der Loopback perfekt ist und die ursprünglichen Bits direkt aus der Nachricht abgeleitet werden können
        # In einem realen Szenario müsste man die ursprünglichen, unkodierten Bits speichern
        
        # Für diesen Testfall können wir die ursprünglichen Bits aus der Nachricht ableiten
        # und dann mit den dekodierten Bits vergleichen
        pass # Wird später im Performance-Test genauer behandelt


@pytest.mark.parametrize("message", [
    "Hello World!",
    "This is a longer test message to check multi-packet transmission.",
    "Short"
])
def test_mfsk_loopback_with_noise(message):
    """Testet den MFSK-Modem-Loopback mit Rauschen und überprüft die Dekodierung."""
    sent_signal, _ = send_text_mfsk(message)

    # Add some noise to the signal
    snr_db = 10 # Example SNR
    signal_power = np.mean(sent_signal**2)
    noise_power = signal_power / (10**(snr_db / 10))
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
    for i in range(min(len(too_corrupted_data), RSC.nsym + 1)): # Mehr Fehler als korrigierbar
        too_corrupted_data[i] ^= 0x01

    # Expect decoding to fail
    with pytest.raises(Exception): # RSC.decode wirft eine Ausnahme bei unkorrigierbaren Fehlern
        RSC.decode(bytes(too_corrupted_data))

