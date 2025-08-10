# SpectraChirp Acoustic Modem

[![Vercel Deployment](https://img.shields.io/badge/Vercel-Live_Demo-black?style=for-the-badge&logo=vercel)](https://spectra-chirp.vercel.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.8+-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge)](https://github.com/psf/black)

SpectraChirp is a Python-based acoustic modem that transmits data through sound waves using Multiple Frequency-Shift Keying (MFSK). **It stands out with its robust error correction (Reed-Solomon), automatic mode detection, reliable synchronization via chirp signals, and the use of Walsh-Hadamard spreading for enhanced signal robustness, ensuring dependable communication even in challenging acoustic environments.** It features a simple web interface and a command-line interface for generating and decoding audio signals, allowing text to be sent from one computer to another using only a microphone and speakers.

### Project Goal & Target Audience

This project was developed primarily as an **educational tool** to demonstrate the principles of digital signal processing and data communication. It is designed for:

*   **Students** studying computer science, electrical engineering, or related fields.
*   **Hobbyists and Makers** interested in radio technology and data-over-sound.
*   **Anyone** curious about how data can be encoded into and decoded from sound waves.

While SpectraChirp is a fully functional acoustic modem, its implementation is intended to be clear and accessible, making it a great starting point for learning and experimentation.

---

## Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Setup and Usage](#setup-and-usage)
- [Project Structure](#project-structure)
- [Getting Help](#getting-help)
- [Contributing](#contributing)
- [Future Improvements](#future-improvements)
- [License](#license)

---

## Features

- **Text-to-Audio Encoding**: Convert any text message into a `.wav` audio file.
- **Audio-to-Text Decoding**: Decode the audio signal back into the original text.
- **MFSK Modulation**: Utilizes MFSK for data transmission.
- **Selectable Modes**:
    - **Default (Fast)**: Higher data rate for clear conditions.
    - **Robust**: Slower, but more resilient to noise.
- **Automatic Mode Detection**: The receiver automatically detects the sender's mode.
- **Error Correction**: Implements Reed-Solomon codes to correct errors caused by noise.
- **Synchronization**: Uses chirp signals to reliably synchronize the start of each data packet.
- **Web-Based UI**: Simple and intuitive frontend built with HTML and JavaScript.
- **Full Character Support**: Reliably transmits and decodes messages containing uppercase and lowercase letters, numbers, and special characters.

---

## How It Works

1.  **Packetization**: The input text is broken down into smaller chunks. Each chunk is placed into a packet containing a header (with packet sequence numbers) and a CRC checksum for integrity verification.
2.  **Forward Error Correction (FEC)**: Reed-Solomon codes are applied to each packet, adding redundant data that allows the receiver to detect and correct errors.
3.  **Modulation (MFSK)**: The binary data of the packet is converted into audio tones. This project uses Walsh-Hadamard spreading to make the signal more robust.
4.  **Synchronization**: A high-frequency "chirp" signal is prepended to each data packet. The receiver listens for this specific chirp to know when a new packet is starting.
5.  **Transmission**: The sequence of tones is saved as a `.wav` file, which can be played through speakers.
6.  **Demodulation & Decoding**: The receiver records the audio, finds the chirp signals, demodulates the tones back into binary data, uses the Reed-Solomon data to fix any errors, and reassembles the original text.

---

## Setup and Installation

### Prerequisites

- Python 3.8+
- `uv` (Python package installer). If you don't have it, install it with `pip install uv`.
- **Audio Hardware**: A working microphone and speakers.
- **System Dependencies**: On some systems (like Linux or macOS with Homebrew), you may need to install the `PortAudio` library, which `sounddevice` depends on.
    ```bash
    # On Debian/Ubuntu
    sudo apt-get install libportaudio2
    # On macOS with Homebrew
    brew install portaudio
    ```

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/saas-erp-hub/SpectraChirp.git
    cd SpectraChirp
    ```

2.  **Install the project:**
    Run the following command in the root directory of the project. This command installs all necessary Python packages and makes the `spectrachirp` command available in your terminal.
    ```bash
    uv pip install -e .
    ```

---

## Usage

You can use SpectraChirp in two ways: through the web interface or the command-line interface.

#### Using the Web Interface

1.  **Start the application:**
    ```bash
    sh start_modem.sh
    ```
    This script will start both the backend server and a local frontend server, and then attempt to open the web interface in your default browser.

2.  **Access the Frontend (if not automatically opened):**
    If the browser does not open automatically, navigate to `http://localhost:8000/index.html` in your web browser.

![SpectraChirp Web UI](https://github.com/saas-erp-hub/SpectraChirp/blob/main/docs/images/web_ui_screenshot.png?raw=true)

#### Using the Command-Line Interface (CLI)

After the installation, the `spectrachirp` command is ready to use directly in your terminal.

![SpectraChirp CLI](https://github.com/saas-erp-hub/SpectraChirp/blob/main/docs/images/cli_screenshot.png?raw=true)

*Examples:*
```bash
# Send a message and save it to a file
spectrachirp send 'hello there' -o modem_signal.wav

# Record a message for 5 seconds and print the result
spectrachirp receive --live --duration 5

# Get help for a specific command
spectrachirp send --help
```

<details open>
<summary><b>► Click to view Full Command Line (CLI) Reference</b></summary>

**Commands:**

-   **`send <text>`**: Generate and transmit an audio signal from text.
    -   `--from-file, -f <path>`: Read message from a text file.
    -   `--output, -o <path>`: Path to save the output WAV file (default: `modem_signal.wav`).
    -   `--mode, -m <mode>`: The MFSK modem mode to use. Available: `DEFAULT`, `FAST`, `ROBUST`.
    -   `--live, -l`: Play the signal directly through speakers.
    -   `--num-tones <int>`: Override number of tones (must be a power of 2).
    -   `--symbol-duration <float>`: Override symbol duration in ms.
    -   `--tone-spacing <float>`: Override tone spacing in Hz.

-   **`receive [input_file]`**: Receive and decode a text message from an audio source.
    -   `--to-file, -t <path>`: Path to a text file to save the decoded message to.
    -   `--live, -l`: Record audio directly from the microphone.
    -   `--duration, -d <seconds>`: Recording duration in seconds for live mode (default: 10).

-   **`analyze <input_file>`**: Inspect an audio file for modem signals and packet data.
-   **`play <input_file>`**: Play an audio file.
-   **`info modes`**: List available MFSK modem modes and their parameters.

</details>

---

## Project Structure

- `frontend/index.html`: The user interface for interacting with the modem.
- `backend/main.py`: The FastAPI backend that serves the API endpoints.
- `backend/modem_mfsk.py`: The core logic for the MFSK modem.
- `backend/tests/`: Unit and integration tests.
- `start_modem.sh`: A simple shell script to start the backend server.
- `docs/`: Contains additional documentation.

---

## Help & Contributing

We welcome feedback and contributions from the community!

*   **Bug Reports:** If you encounter a bug, please open an [issue](https://github.com/saas-erp-hub/SpectraChirp/issues). Be sure to check if a similar issue already exists.
*   **Feature Requests:** Have an idea for a new feature? We'd love to hear it. Please create an [issue](https://github.com/saas-erp-hub/SpectraChirp/issues) to outline your proposal.
*   **Questions:** For general questions or discussions, feel free to open an [issue](https://github.com/saas-erp-hub/SpectraChirp/issues).
*   **Pull Requests:** If you'd like to contribute directly, please read our [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to submit a pull request.

---

## Future Improvements

For a list of potential enhancements and future ideas, please see the [Future Improvements](docs/future_improvements.md) document.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
