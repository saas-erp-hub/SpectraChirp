import numpy as np
import zlib
import io
import soundfile as sf
from scipy.linalg import hadamard
from scipy.signal import chirp
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

# Import configuration from the central config file
from .config import (
    SAMPLE_RATE,
    BASE_FREQ,
    PACKET_CHIRP_DURATION,
    PACKET_CHIRP_F0,
    PACKET_CHIRP_F1,
    PACKET_PAYLOAD_SIZE,
    PACKET_HEADER_SIZE,
    PACKET_CRC_SIZE,
    RS_NSYMS,
    RSC,
    ModemConfig,
    MODEM_MODES,
    MIN_CORRELATION_THRESHOLD,
    SYNC_CORRELATION_THRESHOLD_FACTOR,
)


@dataclass
class PacketAnalysis:
    """Holds the analysis result for a single packet."""

    packet_index: int
    found_at_s: float
    rs_decode_success: bool
    rs_errors_corrected: int
    crc_valid: bool
    packet_num: Optional[int] = None
    total_packets: Optional[int] = None


def bits_to_bytes(bits: str) -> bytes:
    if not bits:
        return b""
    if len(bits) % 8 != 0:
        bits += "0" * (8 - len(bits) % 8)
    return bytes(int(bits[i : i + 8], 2) for i in range(0, len(bits), 8))


def generate_chirp_signal() -> np.ndarray:
    t = np.linspace(
        0,
        PACKET_CHIRP_DURATION,
        int(SAMPLE_RATE * PACKET_CHIRP_DURATION),
        endpoint=False,
    )
    return chirp(
        t,
        f0=PACKET_CHIRP_F0,
        f1=PACKET_CHIRP_F1,
        t1=PACKET_CHIRP_DURATION,
        method="linear",
    )


def _bytes_to_signal(full_packet_bytes: bytes, config: ModemConfig) -> np.ndarray:
    bits = "".join(format(byte, "08b") for byte in full_packet_bytes)
    bit_groups = [
        bits[i : i + config.bits_per_symbol]
        for i in range(0, len(bits), config.bits_per_symbol)
    ]
    if len(bits) % config.bits_per_symbol != 0:
        bit_groups[-1] = bit_groups[-1].ljust(config.bits_per_symbol, "0")

    total_symbols = len(bit_groups)
    signal = np.zeros(total_symbols * config.samples_per_symbol)
    samples_per_chip = config.samples_per_symbol // config.num_tones
    t_chip = np.linspace(
        0,
        config.symbol_duration_ms / 1000 / config.num_tones,
        samples_per_chip,
        endpoint=False,
    )
    frequencies = [BASE_FREQ + i * config.tone_spacing for i in range(config.num_tones)]
    hadamard_matrix = hadamard(config.num_tones)

    for j, group in enumerate(bit_groups):
        symbol_index = int(group, 2)
        walsh_sequence = hadamard_matrix[symbol_index]
        symbol_signal = np.zeros(config.samples_per_symbol)
        phase_shift = np.random.choice([0, np.pi / 2, np.pi, -np.pi / 2])
        for chip_idx, chip_val in enumerate(walsh_sequence):
            frequency = frequencies[chip_idx]
            tone = np.sin(2 * np.pi * frequency * t_chip + phase_shift) * chip_val
            start_chip, end_chip = (
                chip_idx * samples_per_chip,
                (chip_idx + 1) * samples_per_chip,
            )
            symbol_signal[start_chip:end_chip] = tone
        start_symbol, end_symbol = (
            j * config.samples_per_symbol,
            (j + 1) * config.samples_per_symbol,
        )
        signal[start_symbol:end_symbol] = symbol_signal
    return signal


def _prepare_mfsk_packet(chunk: bytes, packet_num: int, total_packets: int) -> bytes:
    header = packet_num.to_bytes(2, "big") + total_packets.to_bytes(2, "big")
    padding = b"\x00" * (PACKET_PAYLOAD_SIZE - len(chunk))
    packet_content = header + chunk + padding
    crc = zlib.crc32(packet_content).to_bytes(PACKET_CRC_SIZE, "big")
    message_with_crc = packet_content + crc
    return RSC.encode(message_with_crc)


def _assemble_mfsk_signal(encoded_message: bytes, config: ModemConfig) -> np.ndarray:
    signal = _bytes_to_signal(encoded_message, config)
    chirp_signal = generate_chirp_signal()
    full_packet_signal = np.concatenate([chirp_signal, signal])
    pause = np.zeros(int(SAMPLE_RATE * 0.1))
    return np.concatenate([full_packet_signal, pause])


def send_text_mfsk(text: str, mode: Union[str, ModemConfig] = "DEFAULT") -> io.BytesIO:
    """
    Generates the MFSK signal, normalizes it, and returns it in an in-memory WAV buffer.
    """
    if isinstance(mode, str):
        config = MODEM_MODES.get(mode, MODEM_MODES["DEFAULT"])
    else:
        config = mode

    byte_data = text.encode("utf-8")
    chunks = [
        byte_data[i : i + PACKET_PAYLOAD_SIZE]
        for i in range(0, len(byte_data), PACKET_PAYLOAD_SIZE)
    ]
    all_packets_signal = np.array([])
    total_chunks = len(chunks)
    for i, chunk in enumerate(chunks):
        encoded_message = _prepare_mfsk_packet(chunk, i + 1, total_chunks)
        packet_signal = _assemble_mfsk_signal(encoded_message, config)
        all_packets_signal = np.concatenate([all_packets_signal, packet_signal])

    # Normalize the signal to prevent clipping
    max_amplitude = np.max(np.abs(all_packets_signal))
    if max_amplitude > 1e-9:
        all_packets_signal /= max_amplitude

    # Write to an in-memory buffer instead of a file
    buffer = io.BytesIO()
    sf.write(buffer, all_packets_signal, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    buffer.seek(0)  # Rewind the buffer to the beginning for reading
    return buffer


def _synchronize_mfsk_signal(
    signal: np.ndarray, config: ModemConfig
) -> tuple[np.ndarray, list[int], int, int]:
    if signal.ndim == 2:
        signal = signal.mean(axis=1)
    target_rms = 0.1
    current_rms = np.sqrt(np.mean(signal**2))
    gain = target_rms / (current_rms + 1e-9)
    signal *= gain
    chirp_template = generate_chirp_signal()
    chirp_len = len(chirp_template)
    correlation = np.correlate(signal, chirp_template, mode="valid")
    if np.max(correlation) < MIN_CORRELATION_THRESHOLD:
        return signal, [], 0, 0
    threshold = np.max(correlation) * SYNC_CORRELATION_THRESHOLD_FACTOR
    peak_indices = np.where(correlation > threshold)[0]
    if not peak_indices.any():
        return signal, [], 0, 0
    bytes_per_packet_encoded = (
        PACKET_HEADER_SIZE + PACKET_PAYLOAD_SIZE + PACKET_CRC_SIZE + RS_NSYMS
    )
    bits_per_packet_encoded = bytes_per_packet_encoded * 8
    symbols_per_packet = (
        bits_per_packet_encoded + config.bits_per_symbol - 1
    ) // config.bits_per_symbol
    samples_per_packet = symbols_per_packet * config.samples_per_symbol
    min_spacing = int(chirp_len + samples_per_packet)
    search_window_size = int(min_spacing * 0.1)
    peaks = [peak_indices[0]]
    last_peak = peak_indices[0]
    while True:
        expected_next_peak = last_peak + min_spacing
        search_start = expected_next_peak - search_window_size
        search_end = expected_next_peak + search_window_size
        if search_end > len(correlation):
            break
        window = correlation[search_start:search_end]
        if len(window) == 0 or np.max(window) < threshold:
            break
        next_peak = search_start + np.argmax(window)
        peaks.append(next_peak)
        last_peak = next_peak
    return signal, peaks, chirp_len, samples_per_packet


def _demodulate_mfsk_symbols(packet_chunk: np.ndarray, config: ModemConfig) -> str:
    received_bits = []
    num_symbols = len(packet_chunk) // config.samples_per_symbol
    frequencies = [BASE_FREQ + i * config.tone_spacing for i in range(config.num_tones)]
    hadamard_matrix = hadamard(config.num_tones)
    samples_per_chip = config.samples_per_symbol // config.num_tones
    for j in range(num_symbols):
        symbol_chunk = packet_chunk[
            j * config.samples_per_symbol : (j + 1) * config.samples_per_symbol
        ]
        if len(symbol_chunk) < config.samples_per_symbol:
            continue
        correlations = np.zeros(len(hadamard_matrix))
        for k, h_row in enumerate(hadamard_matrix):
            correlation_signal_sin = np.zeros(config.samples_per_symbol)
            correlation_signal_cos = np.zeros(config.samples_per_symbol)
            for chip_idx, chip_val in enumerate(h_row):
                t_chip = np.linspace(
                    0,
                    config.symbol_duration_ms / 1000 / config.num_tones,
                    samples_per_chip,
                    endpoint=False,
                )
                ref_tone_sin = (
                    np.sin(2 * np.pi * frequencies[chip_idx] * t_chip) * chip_val
                )
                ref_tone_cos = (
                    np.cos(2 * np.pi * frequencies[chip_idx] * t_chip) * chip_val
                )
                start_idx, end_idx = (
                    chip_idx * samples_per_chip,
                    (chip_idx + 1) * samples_per_chip,
                )
                correlation_signal_sin[start_idx:end_idx] = ref_tone_sin
                correlation_signal_cos[start_idx:end_idx] = ref_tone_cos
            corr_sin = np.sum(symbol_chunk * correlation_signal_sin)
            corr_cos = np.sum(symbol_chunk * correlation_signal_cos)
            correlations[k] = np.sqrt(corr_sin**2 + corr_cos**2)
        best_symbol_index = np.argmax(np.abs(correlations))
        received_bits.append(format(best_symbol_index, f"0{config.bits_per_symbol}b"))
    return "".join(received_bits)


def _verify_crc(packet_content: bytes, received_crc_bytes: bytes) -> bool:
    if len(received_crc_bytes) < PACKET_CRC_SIZE:
        return False
    calculated_crc = zlib.crc32(packet_content)
    received_crc = int.from_bytes(received_crc_bytes, "big")
    return received_crc == calculated_crc


def _decode_mfsk_packet(
    demod_bits_str: str, config: ModemConfig, analyze_mode: bool = False
) -> Tuple[Optional[bytes], Optional[int], Optional[int], int, bool]:
    expected_encoded_bits_len = (
        PACKET_HEADER_SIZE + PACKET_PAYLOAD_SIZE + PACKET_CRC_SIZE + RS_NSYMS
    ) * 8
    if len(demod_bits_str) < expected_encoded_bits_len:
        return None, None, None, -1, False
    demod_bits_str = demod_bits_str[:expected_encoded_bits_len]
    encoded_bytes = bits_to_bytes(demod_bits_str)

    rs_errors_corrected = -1
    crc_ok = False

    try:
        decoded_message, _, errata_pos = RSC.decode(encoded_bytes)
        rs_errors_corrected = len(errata_pos)

        packet_content = decoded_message[: PACKET_HEADER_SIZE + PACKET_PAYLOAD_SIZE]
        received_crc_bytes = decoded_message[PACKET_HEADER_SIZE + PACKET_PAYLOAD_SIZE :]

        crc_ok = _verify_crc(packet_content, received_crc_bytes)

        if crc_ok:
            header = packet_content[:PACKET_HEADER_SIZE]
            payload = packet_content[PACKET_HEADER_SIZE:]
            packet_num = int.from_bytes(header[:2], "big")
            total_packets = int.from_bytes(header[2:], "big")
            return payload, packet_num, total_packets, rs_errors_corrected, True
        else:
            # Still return header info if possible, even with bad CRC, for analysis
            header = packet_content[:PACKET_HEADER_SIZE]
            packet_num = int.from_bytes(header[:2], "big")
            total_packets = int.from_bytes(header[2:], "big")
            return None, packet_num, total_packets, rs_errors_corrected, False

    except Exception:
        return None, None, None, rs_errors_corrected, False


def receive_text_mfsk(
    signal: np.ndarray, mode: str = "DEFAULT"
) -> tuple[str, str, str, str]:
    modes_to_try = [mode] + [m for m in MODEM_MODES if m != mode]
    for current_mode_name in modes_to_try:
        config = MODEM_MODES.get(current_mode_name)
        if not config:
            continue
        current_signal_copy = np.copy(signal)
        current_signal_copy, peaks, chirp_len, samples_per_packet = (
            _synchronize_mfsk_signal(current_signal_copy, config)
        )
        if not peaks:
            continue
        decoded_packets = {}
        max_total_packets = 0
        for peak_start in peaks:
            packet_start = peak_start + chirp_len
            packet_end = packet_start + samples_per_packet
            if packet_end > len(current_signal_copy):
                break
            packet_chunk = current_signal_copy[packet_start:packet_end]
            demod_bits_str = _demodulate_mfsk_symbols(packet_chunk, config)
            decoded_packet_info = _decode_mfsk_packet(demod_bits_str, config)
            payload, packet_num, total_packets, _, crc_ok = decoded_packet_info
            if crc_ok and payload is not None:
                if packet_num not in decoded_packets:
                    decoded_packets[packet_num] = payload
                if total_packets > max_total_packets:
                    max_total_packets = total_packets
            else:
                # In strict decoding, we could break here. For robustness, we continue.
                pass

        # Check if we have a plausible set of packets
        if decoded_packets and max_total_packets > 0:
            # Heuristic: if we decoded at least one packet and have a total count, it's likely the right mode.
            message_parts = [
                decoded_packets.get(i, b"").rstrip(b"\x00")
                for i in range(1, max_total_packets + 1)
            ]
            # Only consider it a success if we have at least one packet
            if any(p != b"" for p in message_parts):
                message = b"".join(message_parts)
                return message.decode("utf-8", "ignore"), "", "", current_mode_name
    return "[Could not detect modem mode or decode message]", "", "", ""


def analyze_signal(signal: np.ndarray) -> tuple[Optional[str], List[PacketAnalysis]]:
    """
    Analyzes a signal for all modem modes and returns detailed packet information.
    """
    for mode_name, config in MODEM_MODES.items():
        analysis_results = []
        current_signal_copy = np.copy(signal)
        current_signal_copy, peaks, chirp_len, samples_per_packet = (
            _synchronize_mfsk_signal(current_signal_copy, config)
        )

        if not peaks:
            continue

        for i, peak_start in enumerate(peaks):
            packet_start = peak_start + chirp_len
            packet_end = packet_start + samples_per_packet
            if packet_end > len(current_signal_copy):
                break

            packet_chunk = current_signal_copy[packet_start:packet_end]
            demod_bits_str = _demodulate_mfsk_symbols(packet_chunk, config)

            _, packet_num, total_packets, rs_errors, crc_ok = _decode_mfsk_packet(
                demod_bits_str, config, analyze_mode=True
            )

            analysis_results.append(
                PacketAnalysis(
                    packet_index=i + 1,
                    found_at_s=peak_start / SAMPLE_RATE,
                    rs_decode_success=(rs_errors != -1),
                    rs_errors_corrected=rs_errors if rs_errors != -1 else 0,
                    crc_valid=crc_ok,
                    packet_num=packet_num,
                    total_packets=total_packets,
                )
            )

        # If we found any packets with a valid CRC, we assume this is the correct mode
        if any(r.crc_valid for r in analysis_results):
            return mode_name, analysis_results

    return None, []
