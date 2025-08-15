"""
Centralized configuration file for the SpectraChirp Acoustic Modem.
"""

from dataclasses import dataclass
from reedsolo import RSCodec

# --- Global Audio Configuration ---
SAMPLE_RATE = 16000
BASE_FREQ = 1000

# --- Packet Structure and Sync Configuration ---
PACKET_CHIRP_DURATION = 0.1
PACKET_CHIRP_F0 = 2500
PACKET_CHIRP_F1 = 3500
MIN_CORRELATION_THRESHOLD = 10  # Minimum correlation value to be considered a potential signal
SYNC_CORRELATION_THRESHOLD_FACTOR = 0.5 # Factor to determine the peak detection threshold from the max correlation
PACKET_PAYLOAD_SIZE = 32  # Size of the data payload in bytes
PACKET_HEADER_SIZE = 4    # Size of the packet header in bytes
PACKET_CRC_SIZE = 4       # Size of the CRC checksum in bytes

# --- Forward Error Correction (FEC) Configuration ---
# Reed-Solomon error correction settings
RS_NSYMS = 16  # Number of ECC symbols to add
RSC = RSCodec(RS_NSYMS)


# --- Modem Mode Definitions ---

@dataclass
class ModemConfig:
    """A data class to hold the configuration for a specific modem mode."""
    name: str
    num_tones: int
    symbol_duration_ms: float
    tone_spacing: float
    samples_per_symbol: int
    bits_per_symbol: int


# Dictionary mapping mode names to their configurations
MODEM_MODES = {
    "DEFAULT": ModemConfig(
        name="DEFAULT",
        num_tones=32,
        symbol_duration_ms=40,
        tone_spacing=35,
        samples_per_symbol=int(SAMPLE_RATE * (40 / 1000.0)),
        bits_per_symbol=5,  # log2(32)
    ),
    "ROBUST": ModemConfig(
        name="ROBUST",
        num_tones=16,
        symbol_duration_ms=60,
        tone_spacing=25,
        samples_per_symbol=int(SAMPLE_RATE * (60 / 1000.0)),
        bits_per_symbol=4,  # log2(16)
    ),
    "FAST": ModemConfig(
        name="FAST",
        num_tones=32,
        symbol_duration_ms=20,
        tone_spacing=50,
        samples_per_symbol=int(SAMPLE_RATE * (20 / 1000.0)),
        bits_per_symbol=5,  # log2(32)
    ),
}
