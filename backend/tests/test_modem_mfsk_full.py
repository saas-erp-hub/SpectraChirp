import pytest
import zlib
import soundfile as sf
from backend.modem_mfsk import send_text_mfsk, receive_text_mfsk, _verify_crc
from backend.config import (
    MODEM_MODES,
    RSC,
    PACKET_PAYLOAD_SIZE,
    PACKET_CRC_SIZE,
    SAMPLE_RATE,
)


# Test data
TEST_TEXT_SHORT = "Hello World!"
TEST_TEXT_LONG = "This is a longer test message to ensure multi-packet transmission and reception works correctly. It should span across several packets to properly test the packetization and reassembly logic. We need enough data to fill more than one payload."


@pytest.mark.parametrize("mode", MODEM_MODES.keys())
def test_mfsk_loopback_short_message(mode):
    """Tests basic send/receive loopback for a short message in different modem modes."""
    buffer = send_text_mfsk(TEST_TEXT_SHORT, mode=mode)
    buffer.seek(0)
    signal, r_samplerate = sf.read(buffer)
    assert r_samplerate == SAMPLE_RATE
    decoded_text, _, _, _ = receive_text_mfsk(signal, mode=mode)
    assert decoded_text == TEST_TEXT_SHORT


@pytest.mark.parametrize("mode", MODEM_MODES.keys())
def test_mfsk_loopback_long_message(mode):
    """Tests basic send/receive loopback for a long message (multi-packet) in different modem modes."""
    buffer = send_text_mfsk(TEST_TEXT_LONG, mode=mode)
    buffer.seek(0)
    signal, r_samplerate = sf.read(buffer)
    assert r_samplerate == SAMPLE_RATE
    decoded_text, _, _, _ = receive_text_mfsk(signal, mode=mode)
    assert decoded_text == TEST_TEXT_LONG


def test_reed_solomon_error_correction():
    """Tests Reed-Solomon error correction capability."""
    original_message = b"This is a test message for Reed-Solomon."

    # Simulate a packet content structure for RS encoding
    # Header + Payload + CRC (dummy values for now)
    dummy_header = b"\x00\x01\x00\x01"  # Packet 1 of 1
    dummy_crc = zlib.crc32(original_message).to_bytes(PACKET_CRC_SIZE, "big")

    # Pad original message to PACKET_PAYLOAD_SIZE if shorter
    padded_message = original_message.ljust(PACKET_PAYLOAD_SIZE, b"\x00")

    message_with_crc = dummy_header + padded_message + dummy_crc

    encoded_message = RSC.encode(message_with_crc)

    # Introduce errors (within correction capability: RS_NSYMS / 2)
    # RS_NSYMS is 16, so can correct up to 8 errors
    corrupted_encoded_message = bytearray(encoded_message)

    # Introduce 5 errors
    errors_to_introduce = 5
    for i in range(errors_to_introduce):
        if i < len(corrupted_encoded_message):  # Ensure we don't go out of bounds
            corrupted_encoded_message[i] = (
                corrupted_encoded_message[i] + 1
            ) % 256  # Flip a bit or change byte

    decoded_message, _, _ = RSC.decode(bytes(corrupted_encoded_message))

    assert decoded_message == message_with_crc


def test_reed_solomon_uncorrectable_errors():
    """Tests that Reed-Solomon fails to decode with too many errors."""
    original_message = b"This is a test message for uncorrectable errors."
    dummy_header = b"\x00\x01\x00\x01"
    dummy_crc = zlib.crc32(original_message).to_bytes(PACKET_CRC_SIZE, "big")
    padded_message = original_message.ljust(PACKET_PAYLOAD_SIZE, b"\x00")
    message_with_crc = dummy_header + padded_message + dummy_crc

    encoded_message = RSC.encode(message_with_crc)

    corrupted_encoded_message = bytearray(encoded_message)

    # Introduce too many errors (more than RS_NSYMS / 2)
    errors_to_introduce = RSC.nsym // 2 + 1  # One more than correctable
    for i in range(errors_to_introduce):
        if i < len(corrupted_encoded_message):
            corrupted_encoded_message[i] = (corrupted_encoded_message[i] + 1) % 256

    with pytest.raises(
        Exception
    ):  # RSC.decode raises an exception on uncorrectable errors
        RSC.decode(bytes(corrupted_encoded_message))


def test_verify_crc():
    """Tests the _verify_crc function with valid and invalid CRCs."""
    # Test with valid CRC
    packet_content = b"test_data"
    calculated_crc = zlib.crc32(packet_content).to_bytes(PACKET_CRC_SIZE, "big")
    assert _verify_crc(packet_content, calculated_crc) is True

    # Test with invalid CRC
    invalid_crc = (zlib.crc32(packet_content) + 1).to_bytes(PACKET_CRC_SIZE, "big")
    assert _verify_crc(packet_content, invalid_crc) is False

    # Test with too short CRC bytes
    short_crc = b"\x00"
    assert _verify_crc(packet_content, short_crc) is False


# def test_packet_crc_integrity():
#     """Tests that packets with incorrect CRC are discarded by receive_text_mfsk."""
#     # This test is complex and appears to be incomplete. It also uses the old, incorrect
#     # signature for send_text_mfsk. Commenting out for now as the core functionality
#     # is implicitly tested by the loopback tests.
#
#     # Send a message
#     signal, all_full_packet_bytes = send_text_mfsk(TEST_TEXT_LONG, mode="DEFAULT")
#
#     # Corrupt the CRC of the first packet in the signal
#     # This is a bit tricky as we need to find the exact location of the first packet's data in the signal
#     # and then corrupt its CRC *after* RS decoding but *before* the CRC check in receive_text_mfsk.
#     # For this test, we'll simulate the corruption by directly manipulating the bytes that would be
#     # passed to the CRC check, rather than trying to corrupt the signal itself.
#     # This tests the CRC check logic within receive_text_mfsk.
#
#     # We need to simulate the scenario where RS decoding *succeeds* but the CRC is wrong.
#     # Let's create a known good packet and then a corrupted version of its CRC.
#
#     # Take the first encoded packet bytes
#     first_encoded_packet = all_full_packet_bytes[0]
#
#     # Decode it to get the message_with_crc
#     decoded_message_good, _, _ = RSC.decode(first_encoded_packet)
#
#     # Now, create a version where the CRC is intentionally wrong
#     packet_content_good = decoded_message_good[
#         : PACKET_HEADER_SIZE + PACKET_PAYLOAD_SIZE
#     ]
#     received_crc_bytes_good = decoded_message_good[
#         PACKET_HEADER_SIZE + PACKET_PAYLOAD_SIZE :
#     ]
#
#     # Corrupt the CRC bytes
#     corrupted_crc_bytes = bytearray(received_crc_bytes_good)
#     if len(corrupted_crc_bytes) > 0:
#         corrupted_crc_bytes[0] = (corrupted_crc_bytes[0] + 1) % 256  # Flip a byte
#     else:
#         # Handle case where CRC bytes might be empty (shouldn't happen with PACKET_CRC_SIZE > 0)
#         pytest.skip("Cannot corrupt CRC bytes as they are empty.")
#
#     # Reconstruct a "decoded_message" with the bad CRC
#     decoded_message_bad_crc = packet_content_good + bytes(corrupted_crc_bytes)
#
#     # Now, how to make receive_text_mfsk process this specific corrupted packet?
#     # We can't easily inject a single corrupted packet into the signal and expect
#     # receive_text_mfsk to isolate it perfectly for this specific test.
#     # A more direct way to test the CRC check is to mock the RSC.decode result
#     # or to test the CRC logic in isolation if it were a separate function.
#
#     # Given the current structure, the best way to test this is to ensure that
#     # if a packet's CRC is bad, it's not included in the final decoded message.
#     # We'll rely on the loopback test to show success, and then conceptually
#     # understand that if a packet fails CRC, it's not in decoded_packets.
#
#     # For a direct test of CRC rejection, we would need to modify receive_text_mfsk
#     # to allow injecting a pre-decoded packet with a bad CRC, or make the CRC check
#     # a separate, testable function.
#
#     # For now, the loopback tests cover this sufficiently for now, as a bad CRC
#     # would lead to a failed assertion in the loopback.
#     pass  # Placeholder, as direct injection is complex without refactoring
