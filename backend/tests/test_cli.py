import pytest
import typer
from typer.testing import CliRunner
from unittest.mock import patch, mock_open, MagicMock
import numpy as np

from cli import app, MODEM_MODES, SAMPLE_RATE, ModemConfig, PacketAnalysis

runner = CliRunner()

# Mock external dependencies
@pytest.fixture(autouse=True)
def mock_external_dependencies():
    with patch("cli.sd") as mock_sd, \
         patch("cli.sf") as mock_sf, \
         patch("builtins.open", new_callable=mock_open) as mock_builtin_open, \
         patch("cli.send_text_mfsk") as mock_send_text_mfsk, \
         patch("cli.receive_text_mfsk") as mock_receive_text_mfsk, \
         patch("cli.analyze_signal") as mock_analyze_signal:
        
        # Configure mocks
        mock_sd.rec.return_value = np.ones(SAMPLE_RATE * 5) # 5 seconds of non-zero signal
        mock_sd.wait.return_value = None
        mock_sd.play.return_value = None

        mock_sf.read.return_value = (np.ones(SAMPLE_RATE * 5), SAMPLE_RATE)
        mock_sf.write.return_value = None

        # Default return for modem functions
        mock_send_text_mfsk.return_value = (np.zeros(1000), None)
        mock_receive_text_mfsk.return_value = ("decoded message", None, None, "DEFAULT")
        mock_analyze_signal.return_value = ("DEFAULT", [])

        yield # This yields control to the test function

# Helper to run commands and capture output
def run_command(command, *args, **kwargs):
    return runner.invoke(app, [command, *args], **kwargs)

# --- Test `info modes` command ---
def test_list_modes():
    result = run_command("info", "modes")
    assert result.exit_code == 0
    assert "Available MFSK Modes:" in result.stdout
    for mode_name in MODEM_MODES.keys():
        assert f"--- {mode_name} ---" in result.stdout

# --- Test `send` command ---
def test_send_text_direct_and_save_to_file():
    with patch("cli.typer.secho") as mock_secho:
        result = run_command("send", "hello", "-o", "test.wav")
        assert result.exit_code == 0
        mock_secho.assert_any_call(
            "Successfully generated signal and saved to 'test.wav'",
            fg=typer.colors.GREEN
        )
        assert "Encoding text: 'hello'" in result.stdout

def test_send_from_file_and_save_to_file():
    with patch("cli.typer.secho") as mock_secho, \
         patch("builtins.open", mock_open(read_data="file content")) as mock_file_open:
        result = run_command("send", "--from-file", "input.txt", "-o", "test.wav")
        assert result.exit_code == 0
        mock_file_open.assert_called_once_with("input.txt", 'r')
        mock_secho.assert_any_call(
            "Successfully generated signal and saved to 'test.wav'",
            fg=typer.colors.GREEN
        )
        assert "Reading message from 'input.txt'" in result.stdout

def test_send_live_mode():
    with patch("cli.typer.secho") as mock_secho, \
         patch("cli.sd.play") as mock_sd_play:
        result = run_command("send", "live test", "--live")
        assert result.exit_code == 0
        mock_sd_play.assert_called_once()
        mock_secho.assert_any_call("Playback complete.", fg=typer.colors.GREEN)

def test_send_expert_mode_success():
    with patch("cli.typer.secho") as mock_secho, \
         patch("cli.send_text_mfsk", return_value=(np.ones(1000), None)) as mock_send_text_mfsk:
        result = run_command("send", "expert test", "--num-tones", "8",
                             "--symbol-duration", "120", "--tone-spacing", "20")
        assert result.exit_code == 0
        mock_secho.assert_any_call("Expert mode activated. Using custom parameters.",
                                   fg=typer.colors.YELLOW)
        mock_send_text_mfsk.assert_called_once()
        assert isinstance(mock_send_text_mfsk.call_args[1]['mode'], ModemConfig)

def test_send_error_no_text_or_file():
    with patch("cli.typer.secho") as mock_secho:
        result = run_command("send")
        assert result.exit_code == 1
        mock_secho.assert_any_call(
            "Error: You must provide a text message directly or use the --from-file option.",
            fg=typer.colors.RED
        )

def test_send_error_both_text_and_file():
    with patch("cli.typer.secho") as mock_secho:
        result = run_command("send", "text", "--from-file", "file.txt")
        assert result.exit_code == 1
        mock_secho.assert_any_call(
            "Error: You cannot provide a text message directly and use --from-file at the same time.",
            fg=typer.colors.RED
        )

def test_send_error_file_not_found():
    with patch("cli.typer.secho") as mock_secho, \
         patch("builtins.open", side_effect=FileNotFoundError):
        result = run_command("send", "--from-file", "nonexistent.txt")
        assert result.exit_code == 1
        mock_secho.assert_any_call(
            "Error: Input file not found at 'nonexistent.txt'",
            fg=typer.colors.RED
        )

def test_send_error_invalid_mode():
    with patch("cli.typer.secho") as mock_secho:
        result = run_command("send", "test", "--mode", "INVALID")
        assert result.exit_code == 1
        mock_secho.assert_any_call(
            "Error: Invalid mode 'INVALID'. Please choose from ['DEFAULT', 'ROBUST', 'FAST'].",
            fg=typer.colors.RED
        )

def test_send_error_expert_mode_missing_params():
    with patch("cli.typer.secho") as mock_secho:
        result = run_command("send", "expert test", "--num-tones", "8")
        assert result.exit_code == 1
        mock_secho.assert_any_call(
            "Error: For expert mode, you must provide --num-tones, "
            "--symbol-duration, and --tone-spacing.",
            fg=typer.colors.RED
        )

def test_send_error_expert_mode_invalid_num_tones():
    with patch("cli.typer.secho") as mock_secho:
        result = run_command("send", "expert test", "--num-tones", "7",
                             "--symbol-duration", "120", "--tone-spacing", "20")
        assert result.exit_code == 1
        mock_secho.assert_any_call(
            "Error: --num-tones must be a power of 2 (e.g., 8, 16, 32).",
            fg=typer.colors.RED
        )

def test_send_error_playback_failure():
    with patch("cli.typer.secho") as mock_secho, \
         patch("cli.sd.play", side_effect=Exception("Playback error")):
        result = run_command("send", "test", "--live")
        assert result.exit_code == 1
        mock_secho.assert_any_call(
            "Error playing audio: Playback error",
            fg=typer.colors.RED
        )

def test_send_error_file_write_failure():
    with patch("cli.typer.secho") as mock_secho, \
         patch("cli.sf.write", side_effect=Exception("Write error")):
        result = run_command("send", "test", "-o", "bad.wav")
        assert result.exit_code == 1
        mock_secho.assert_any_call(
            "Error writing file: Write error",
            fg=typer.colors.RED
        )

# --- Test `receive` command ---
def test_receive_from_file_success():
    with patch("cli.typer.secho") as mock_secho, \
         patch("cli.receive_text_mfsk", return_value=("decoded text", None, None, "DEFAULT")):
        result = run_command("receive", "input.wav")
        assert result.exit_code == 0
        mock_secho.assert_any_call("Decoded Message:", fg=typer.colors.CYAN)
        assert "decoded text" in result.stdout

def test_receive_from_file_and_save_to_file():
    with patch("cli.typer.secho") as mock_secho, \
         patch("cli.receive_text_mfsk", return_value=("decoded text", None, None, "DEFAULT")), \
         patch("builtins.open", mock_open()) as mock_file_open:
        result = run_command("receive", "input.wav", "--to-file", "output.txt")
        assert result.exit_code == 0
        mock_file_open.assert_called_once_with("output.txt", 'w')
        mock_file_open().write.assert_called_once_with("decoded text")
        mock_secho.assert_any_call(
            "Decoded message saved to 'output.txt'",
            fg=typer.colors.GREEN
        )

def test_receive_live_success():
    with patch("cli.typer.secho") as mock_secho, \
         patch("cli.sd.rec", return_value=np.ones(SAMPLE_RATE * 5)), \
         patch("cli.receive_text_mfsk", return_value=("live decoded", None, None, "DEFAULT")):
        result = run_command("receive", "--live", "--duration", "1")
        assert result.exit_code == 0
        mock_secho.assert_any_call("Decoded Message:", fg=typer.colors.CYAN)
        assert "live decoded" in result.stdout
        assert "Recording for 1 seconds..." in result.stdout

def test_receive_error_no_input():
    with patch("cli.typer.secho") as mock_secho:
        result = run_command("receive")
        assert result.exit_code == 1
        mock_secho.assert_any_call(
            "Error: You must specify an input file or use the --live flag.",
            fg=typer.colors.RED
        )

def test_receive_error_file_read_failure():
    with patch("cli.typer.secho") as mock_secho, \
         patch("cli.sf.read", side_effect=Exception("Read error")):
        result = run_command("receive", "bad.wav")
        assert result.exit_code == 1
        mock_secho.assert_any_call(
            "Error reading file 'bad.wav': Read error",
            fg=typer.colors.RED
        )

def test_receive_error_no_signal_to_process():
    with patch("cli.typer.secho") as mock_secho, \
         patch("cli.sf.read", return_value=(np.array([]), SAMPLE_RATE)):
        result = run_command("receive", "empty.wav")
        assert result.exit_code == 1
        mock_secho.assert_any_call(
            "No audio signal to process.",
            fg=typer.colors.RED
        )

def test_receive_error_decode_failure():
    with patch("cli.typer.secho") as mock_secho, \
         patch("cli.receive_text_mfsk", return_value=(None, None, None, None)):
        result = run_command("receive", "input.wav")
        assert result.exit_code == 1
        mock_secho.assert_any_call(
            "Failed to decode the message. The signal may be too noisy or not a valid modem signal.",
            fg=typer.colors.RED
        )

def test_receive_warning_sample_rate_mismatch():
    with patch("cli.typer.secho") as mock_secho,          patch("cli.sf.read", return_value=(np.ones(1000), 22050)): # Mismatched sample rate
        result = run_command("receive", "input.wav")
        assert result.exit_code == 0
        mock_secho.assert_any_call(
            f"Warning: File sample rate (22050 Hz) differs from modem rate ({SAMPLE_RATE} Hz).",
            fg=typer.colors.YELLOW
        )

# --- Test `analyze` command ---
def test_analyze_success():
    mock_analysis_results = [
        PacketAnalysis(packet_index=0, found_at_s=1.23, rs_decode_success=True,
                       rs_errors_corrected=5, crc_valid=True, packet_num=1,
                       total_packets=1)
    ]
    with patch("cli.typer.secho") as mock_secho, \
         patch("cli.analyze_signal", return_value=("DEFAULT", mock_analysis_results)):
        result = run_command("analyze", "input.wav")
        assert result.exit_code == 0
        mock_secho.assert_any_call("Detected Signal Mode: DEFAULT", fg=typer.colors.CYAN)
        assert "Found 1 potential packet(s):" in result.stdout
        assert "--- Packet 0 ---" in result.stdout
        assert "  - Found at: 1.23 seconds" in result.stdout
        mock_secho.assert_any_call("  - Reed-Solomon Decode: OK", fg=typer.colors.GREEN)
        assert "  - RS Errors Corrected: 5" in result.stdout
        mock_secho.assert_any_call("  - CRC Check: OK", fg=typer.colors.GREEN)
        assert "  - Header: Packet 1 of 1" in result.stdout

def test_analyze_no_signal_detected():
    with patch("cli.typer.secho") as mock_secho, \
         patch("cli.analyze_signal", return_value=(None, [])):
        result = run_command("analyze", "input.wav")
        assert result.exit_code == 1
        mock_secho.assert_any_call(
            "Analysis complete: No valid MFSK signal detected.",
            fg=typer.colors.RED
        )

def test_analyze_error_file_read_failure():
    with patch("cli.typer.secho") as mock_secho, \
         patch("cli.sf.read", side_effect=Exception("Read error")):
        result = run_command("analyze", "bad.wav")
        assert result.exit_code == 1
        mock_secho.assert_any_call(
            "Error reading file 'bad.wav': Read error",
            fg=typer.colors.RED
        )

def test_analyze_warning_sample_rate_mismatch():
    with patch("cli.typer.secho") as mock_secho, \
         patch("cli.sf.read", return_value=(np.ones(1000), 22050)): # Mismatched sample rate

        result = run_command("analyze", "input.wav")
        assert result.exit_code == 0
        mock_secho.assert_any_call(
            f"Warning: File sample rate (22050 Hz) differs from modem rate ({SAMPLE_RATE} Hz).",
            fg=typer.colors.YELLOW
        )

# --- Test `play` command ---
def test_play_success():
    with patch("cli.typer.secho") as mock_secho, \
         patch("cli.sd.play") as mock_sd_play:
        result = run_command("play", "audio.wav")
        assert result.exit_code == 0
        mock_sd_play.assert_called_once()
        mock_secho.assert_any_call("Playback complete.", fg=typer.colors.GREEN)
        assert "Playing audio from 'audio.wav'..." in result.stdout

def test_play_error_file_read_failure():
    with patch("cli.typer.secho") as mock_secho, \
         patch("cli.sf.read", side_effect=Exception("Play read error")):
        result = run_command("play", "bad.wav")
        assert result.exit_code == 1
        mock_secho.assert_any_call(
            "Error playing file 'bad.wav': Play read error",
            fg=typer.colors.RED
        )

def test_play_warning_sample_rate_mismatch():
    with patch("cli.typer.secho") as mock_secho,          patch("cli.sf.read", return_value=(np.ones(1000), 22050)): # Mismatched sample rate
        result = run_command("play", "input.wav")
        assert result.exit_code == 0
        mock_secho.assert_any_call(
            f"Warning: File sample rate (22050 Hz) differs from modem rate ({SAMPLE_RATE} Hz).",
            fg=typer.colors.YELLOW
        )
