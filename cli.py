import typer
from typing_extensions import Annotated
import soundfile as sf
import numpy as np
import os
import sys
from typing import Optional

# Attempt to import sounddevice and provide a helpful error message if it's missing.
try:
    import sounddevice as sd
except ImportError:
    print("Error: The 'sounddevice' library is required for live mode. "
          "Please install it.")
    print("You can typically install it by running: "
          "uv pip install -r backend/requirements.txt")
    sys.exit(1)


from backend.modem_mfsk import (
    send_text_mfsk, receive_text_mfsk, analyze_signal,
    MODEM_MODES, SAMPLE_RATE, PacketAnalysis, ModemConfig
)

# Dynamically create the help text for the --mode option
mode_help = ("The MFSK modem mode to use. Available: DEFAULT, "
             "FAST (for speed), ROBUST (for reliability).")

# --- Examples Epilog --- #

epilog_text = """
Examples:

  1. Send a message and save it to a file:			spectrachirp send 'hello world' -o message.wav

  2. Play back the generated audio file:				spectrachirp play message.wav

  3. Record a message for 5 seconds and print the result:		spectrachirp receive --live --duration 5

  4. Decode a message from a file and save the result:		spectrachirp receive message.wav --to-file decoded.txt

  Send a message live using a specific mode:			spectrachirp send 'live message' --mode FAST --live

  6. Analyze a signal file for packet information:		spectrachirp analyze message.wav

  7. List detailed information about available modem modes:	spectrachirp info modes

  8. Get help for a specific command (e.g., send):		spectrachirp send --help
"""




app = typer.Typer(
    name="SpectraChirp CLI",
    help="A robust acoustic modem for transmitting data through sound.",
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    epilog=epilog_text
)

# Create a subcommand for info-related commands
info_app = typer.Typer(name="info", help="Display detailed information about modem configurations.")
app.add_typer(info_app)


@info_app.command("modes", help="List available MFSK modem modes and their parameters.")
def list_modes():
    typer.secho("Available MFSK Modes:", fg=typer.colors.CYAN)
    for name, config in MODEM_MODES.items():
        typer.echo(f"\n--- {name} ---")
        typer.echo(f"  - Tones: {config.num_tones}")
        typer.echo(f"  - Symbol Duration: {config.symbol_duration_ms} ms")
        typer.echo(f"  - Tone Spacing: {config.tone_spacing} Hz")
        typer.echo(f"  - Bits per Symbol: {config.bits_per_symbol}")


@app.command(
    help="Generate and transmit an audio signal from text.",
    epilog="""
Examples:
  Send a simple message and save to 'modem_signal.wav':
    spectrachirp send 'hello there'

  Send from a file and save to a custom audio file:
    spectrachirp send --from-file message.txt -o custom.wav

  Send a message in ROBUST mode and play it live:
    spectrachirp send "live robust" --mode ROBUST --live
    
  Send using custom expert parameters:
    spectrachirp send "expert" --num-tones 8 --symbol-duration 120 --tone-spacing 20

  Get help for the send command:
    spectrachirp send --help
"""
)
def send(
    text: Annotated[Optional[str], typer.Argument(
        help="The text message to encode. If not provided, --from-file must be used."
    )] = None,
    # File Options
    from_file: Annotated[Optional[str], typer.Option(
        "--from-file", "-f",
        help="Path to a text file to read the message from.",
        rich_help_panel="File Options"
    )] = None,
    output_file: Annotated[str, typer.Option(
        "--output", "-o",
        help="Path to save the output WAV file.",
        rich_help_panel="File Options"
    )] = "modem_signal.wav",
    # Mode Options
    mode: Annotated[str, typer.Option(
        "--mode", "-m",
        help=mode_help,
        case_sensitive=False,
        rich_help_panel="Mode Options"
    )] = "DEFAULT",
    live: Annotated[bool, typer.Option(
        "--live", "-l",
        help="Play the signal directly through speakers.",
        rich_help_panel="Mode Options"
    )] = False,
    # Expert Options
    num_tones: Annotated[Optional[int], typer.Option(
        "--num-tones", help="Override number of tones (must be a power of 2).",
        rich_help_panel="Expert Options"
    )] = None,
    symbol_duration_ms: Annotated[Optional[float], typer.Option(
        "--symbol-duration", help="Override symbol duration in ms.",
        rich_help_panel="Expert Options"
    )] = None,
    tone_spacing: Annotated[Optional[float], typer.Option(
        "--tone-spacing", help="Override tone spacing in Hz.",
        rich_help_panel="Expert Options"
    )] = None,
):
    if text is None and from_file is None:
        typer.secho("Error: You must provide a text message directly or use "
                    "the --from-file option.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    if text and from_file:
        typer.secho("Error: You cannot provide a text message directly and use "
                    "--from-file at the same time.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if from_file:
        try:
            with open(from_file, 'r') as f: text_to_send = f.read()
            typer.echo(f"Reading message from '{from_file}'")
        except FileNotFoundError:
            typer.secho(f"Error: Input file not found at '{from_file}'",
                        fg=typer.colors.RED)
            raise typer.Exit(code=1)
    else: text_to_send = text

    expert_params = [num_tones, symbol_duration_ms, tone_spacing]
    is_expert_mode = any(p is not None for p in expert_params)
    config_to_use = None

    if is_expert_mode:
        typer.secho("Expert mode activated. Using custom parameters.", fg=typer.colors.YELLOW)
        if not all(p is not None for p in expert_params):
            typer.secho("Error: For expert mode, you must provide --num-tones, "
                        "--symbol-duration, and --tone-spacing.",
                        fg=typer.colors.RED)
            raise typer.Exit(code=1)
        if not (num_tones & (num_tones - 1) == 0) or num_tones == 0:
             typer.secho("Error: --num-tones must be a power of 2 (e.g., 8, 16, 32).",
                         fg=typer.colors.RED)
             raise typer.Exit(code=1)
        bits_per_symbol = int(np.log2(num_tones))
        samples_per_symbol = int(SAMPLE_RATE * (symbol_duration_ms / 1000.0))
        config_to_use = ModemConfig("EXPERT", num_tones, symbol_duration_ms,
                                    tone_spacing, samples_per_symbol,
                                    bits_per_symbol)
        typer.echo(f"Using custom config: {config_to_use}")
    else:
        if mode.upper() not in MODEM_MODES:
            typer.secho(f"Error: Invalid mode '{mode}'. Please choose from "
                        f"{list(MODEM_MODES.keys())}.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        config_to_use = mode.upper()
        typer.echo(f"Using mode: {config_to_use}")

    typer.echo(f"Encoding text: '{text_to_send[:100]}"
               f"{'...' if len(text_to_send) > 100 else ''}'")
    
    # The function now returns a BytesIO buffer with the WAV data
    wav_buffer = send_text_mfsk(text_to_send, mode=config_to_use)

    if live:
        try:
            # Read the data from the buffer for playback
            wav_buffer.seek(0)
            signal, samplerate = sf.read(wav_buffer)
            if samplerate != SAMPLE_RATE:
                typer.secho(f"Warning: Internal sample rate mismatch. Expected {SAMPLE_RATE}, got {samplerate}", fg=typer.colors.YELLOW)

            typer.echo("Playing audio signal...")
            sd.play(signal, SAMPLE_RATE)
            sd.wait()
            typer.secho("Playback complete.", fg=typer.colors.GREEN)
        except Exception as e:
            typer.secho(f"Error playing audio: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    else:
        try:
            # Write the buffer's content directly to the output file
            wav_buffer.seek(0)
            with open(output_file, 'wb') as f:
                f.write(wav_buffer.read())
            typer.secho(f"Successfully generated signal and saved to "
                        f"'{output_file}'", fg=typer.colors.GREEN)
        except Exception as e:
            typer.secho(f"Error writing file: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)


@app.command(
    help="Receive and decode a text message from an audio source.",
    epilog="""
Examples:
  Decode from the default 'modem_signal.wav' file:
    spectrachirp receive modem_signal.wav

  Record live for 5 seconds and print the decoded message:
    spectrachirp receive --live --duration 5

  Decode from a file and save the output to another file:
    spectrachirp receive input.wav --to-file decoded.txt
"""
)
def receive(
    input_file: Annotated[Optional[str], typer.Argument(
        help="Path to the input WAV file to decode. Ignored in --live mode."
    )] = None,
    # File Options
    to_file: Annotated[Optional[str], typer.Option(
        "--to-file", "-t",
        help="Path to a text file to save the decoded message to.",
        rich_help_panel="File Options"
    )] = None,
    # Live Options
    live: Annotated[bool, typer.Option(
        "--live", "-l",
        help="Record audio directly from the microphone.",
        rich_help_panel="Live Options"
    )] = False,
    duration: Annotated[int, typer.Option(
        "--duration", "-d",
        help="Recording duration in seconds for live mode.",
        rich_help_panel="Live Options"
    )] = 10,
):
    signal = None
    if live:
        if input_file:
            typer.secho("Warning: Input file argument is ignored when using "
                        "--live mode.", fg=typer.colors.YELLOW)
        try:
            typer.echo(f"Recording for {duration} seconds... "
                       "Press Ctrl+C to stop early.")
            recording = sd.rec(int(duration * SAMPLE_RATE),
                               samplerate=SAMPLE_RATE, channels=1)
            sd.wait()
            typer.echo("Recording finished.")
            signal = recording.flatten()
        except KeyboardInterrupt:
            typer.echo("\nRecording stopped by user.")
            sd.stop()
            signal = sd.rec(int(duration * SAMPLE_RATE),
                            samplerate=SAMPLE_RATE, channels=1).flatten()
        except Exception as e:
            typer.secho(f"Error during recording: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    elif input_file:
        try:
            signal, sample_rate = sf.read(input_file)
            if sample_rate != SAMPLE_RATE:
                typer.secho(f"Warning: File sample rate ({sample_rate} Hz) "
                            f"differs from modem rate ({SAMPLE_RATE} Hz).",
                            fg=typer.colors.YELLOW)
        except Exception as e:
            typer.secho(f"Error reading file '{input_file}': {e}",
                        fg=typer.colors.RED)
            raise typer.Exit(code=1)
    else:
        typer.secho("Error: You must specify an input file or use the --live flag.", fg=typer.colors.RED); raise typer.Exit(code=1)

    if signal is None or not signal.any():
        typer.secho("No audio signal to process.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo("Decoding signal...")
    decoded_text, _, _, detected_mode = receive_text_mfsk(signal)

    if detected_mode:
        typer.echo(f"Automatically detected mode: {detected_mode}")
        if to_file:
            try:
                with open(to_file, 'w') as f: f.write(decoded_text)
                typer.secho(f"Decoded message saved to '{to_file}'",
                            fg=typer.colors.GREEN)
            except Exception as e:
                typer.secho(f"Error writing to file: {e}", fg=typer.colors.RED)
                raise typer.Exit(code=1)
        else:
            typer.secho("Decoded Message:", fg=typer.colors.CYAN)
            typer.echo(decoded_text)
    else:
        typer.secho("Failed to decode the message. The signal may be too noisy "
                    "or not a valid modem signal.", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command(
    help="Inspect an audio file for modem signals and packet data.",
    epilog="""
Example:
  Analyze a signal and see detailed packet information:
    spectrachirp analyze input_signal.wav
"""
)
def analyze(
    input_file: Annotated[str, typer.Argument(help="Path to the WAV file to analyze.")],
):
    try:
        signal, sample_rate = sf.read(input_file)
        if sample_rate != SAMPLE_RATE:
            typer.secho(f"Warning: File sample rate ({sample_rate} Hz) "
                        f"differs from modem rate ({SAMPLE_RATE} Hz).",
                        fg=typer.colors.YELLOW)
    except Exception as e:
        typer.secho(f"Error reading file '{input_file}': {e}", fg=typer.colors.RED); raise typer.Exit(code=1)

    typer.echo(f"Analyzing signal from '{input_file}'...")
    detected_mode, analysis_results = analyze_signal(signal)

    if not detected_mode:
        typer.secho("Analysis complete: No valid MFSK signal detected.",
                    fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(f"Detected Signal Mode: {detected_mode}", fg=typer.colors.CYAN)
    typer.echo("-" * 40)
    typer.echo(f"Found {len(analysis_results)} potential packet(s):")

    for result in analysis_results:
        typer.echo(f"\n--- Packet {result.packet_index} ---")
        typer.echo(f"  - Found at: {result.found_at_s:.2f} seconds")
        rs_status = "OK" if result.rs_decode_success else "FAIL"
        rs_color = (typer.colors.GREEN if result.rs_decode_success
                    else typer.colors.RED)
        typer.secho(f"  - Reed-Solomon Decode: {rs_status}", fg=rs_color)
        if result.rs_decode_success: typer.echo(f"  - RS Errors Corrected: {result.rs_errors_corrected}")
        crc_status = "OK" if result.crc_valid else "FAIL"
        crc_color = (typer.colors.GREEN if result.crc_valid
                     else typer.colors.RED)
        typer.secho(f"  - CRC Check: {crc_status}", fg=crc_color)
        if result.packet_num is not None: typer.echo(f"  - Header: Packet {result.packet_num} of {result.total_packets}")
    typer.echo("-" * 40)


@app.command(
    help="Play an audio file.",
    epilog="""
Example:
  Play a generated message:
    spectrachirp play message.wav
"""
)
def play(
    input_file: Annotated[str, typer.Argument(help="Path to the WAV file to play.")],
):
    try:
        signal, sample_rate = sf.read(input_file)
        if sample_rate != SAMPLE_RATE:
            typer.secho(f"Warning: File sample rate ({sample_rate} Hz) "
                        f"differs from modem rate ({SAMPLE_RATE} Hz).",
                        fg=typer.colors.YELLOW)
        typer.echo(f"Playing audio from '{input_file}'...")
        sd.play(signal, sample_rate)
        sd.wait()
        typer.secho("Playback complete.", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"Error playing file '{input_file}': {e}",
                    fg=typer.colors.RED)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()