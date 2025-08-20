const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://127.0.0.1:8001"
  : "";
const sendBtn = document.getElementById('send-btn');
const clearBtn = document.getElementById('clear-btn');
const inputText = document.getElementById('input-text');
const modeSelect = document.getElementById('mode-select'); // Get the mode dropdown
const output = document.getElementById('output');
const downloadLink = document.getElementById('download-link');
const audioPlayer = document.getElementById('audio-player');
const sendSpinner = document.getElementById('send-spinner');

const fileInput = document.getElementById('fileInput');
const selectFileButton = document.getElementById('selectFileButton');
const fileNameDisplay = document.getElementById('fileNameDisplay');

selectFileButton.onclick = () => {
  fileInput.click();
};

fileInput.onchange = () => {
  if (fileInput.files.length > 0) {
    fileNameDisplay.textContent = fileInput.files[0].name;
    // Also trigger decode if a file is selected
    decodeBlob(fileInput.files[0], fileInput.files[0].name);
  } else {
    fileNameDisplay.textContent = 'No file chosen';
  }
};
const decodeBtn = document.getElementById('decode-btn');
const decodeOutput = document.getElementById('decode-output');
const decodedModeDisplay = document.getElementById('decodedModeDisplay');
const decodeSpinner = document.getElementById('decode-spinner');
const copyDecodedBtn = document.getElementById('copy-decoded-btn');

// Live recording elements
const recordBtn = document.getElementById('record-btn');
const stopBtn = document.getElementById('stop-btn');
const recordStatus = document.getElementById('record-status');
let mediaRecorder;
let audioChunks = [];


// Send (Generate Signal)
sendBtn.onclick = async () => {
  const msg = inputText.value.trim();
  const modem = 'mfsk';
  const mode = modeSelect.value; // Get selected mode from dropdown

  output.textContent = "";
  downloadLink.style.display = "none";
  audioPlayer.style.display = "none";
  inputText.classList.remove('input-error'); // Clear previous error

  if (!msg) {
    output.innerHTML = `<span class="status-error">Error: Please enter a message!</span>`;
    inputText.classList.add('input-error'); // Highlight input
    return;
  }
  sendBtn.disabled = true;
  sendSpinner.style.display = 'inline-block'; // Show spinner
  output.textContent = "Generating signal...";

  try {
    const res = await fetch(`${API_BASE}/generate_signal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: msg, modem, mode })
    });

    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `HTTP Error ${res.status}`);
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);

    downloadLink.href = url;
    downloadLink.download = "modem_signal.wav";
    downloadLink.textContent = "Download Audio";
    downloadLink.style.display = "block";

    audioPlayer.src = url;
    audioPlayer.style.display = "block";
    output.innerHTML = `<span class="status-success">Signal generated!</span>`;

  } catch (e) {
    output.innerHTML = `<span class="status-error">Error sending: ${e.message}</span>`;
  } finally {
    sendBtn.disabled = false;
    sendSpinner.style.display = 'none'; // Hide spinner
  }
};

clearBtn.onclick = () => {
  inputText.value = "";
  output.textContent = "";
  downloadLink.style.display = "none";
  audioPlayer.style.display = "none";
  inputText.classList.remove('input-error'); // Clear error on clear
};

// --- Decode Logic ---

function encodeWAV(audioBuffer) {
    const numOfChan = audioBuffer.numberOfChannels;
    const samples = audioBuffer.getChannelData(0); // Assuming mono for simplicity, or handle multiple channels

    const dataLength = samples.length * numOfChan * 2; // 2 bytes per sample
    const buffer = new ArrayBuffer(44 + dataLength);
    const view = new DataView(buffer);

    /* RIFF identifier */
    writeString(view, 0, 'RIFF');
    /* file length */
    view.setUint32(4, 36 + dataLength, true);
    /* RIFF type */
    writeString(view, 8, 'WAVE');
    /* format chunk identifier */
    writeString(view, 12, 'fmt ');
    /* format chunk length */
    view.setUint32(16, 16, true);
    /* sample format (raw) */
    view.setUint16(20, 1, true);
    /* channel count */
    view.setUint16(22, numOfChan, true);
    /* sample rate */
    view.setUint32(24, audioBuffer.sampleRate, true);
    /* byte rate (sample rate * block align) */
    view.setUint32(28, audioBuffer.sampleRate * numOfChan * 2, true);
    /* block align (channel count * bytes per sample) */
    view.setUint16(32, numOfChan * 2, true);
    /* bits per sample */
    view.setUint16(34, 16, true);
    /* data chunk identifier */
    writeString(view, 36, 'data');
    /* data chunk length */
    view.setUint32(40, dataLength, true);

    floatTo16BitPCM(view, 44, samples);

    return new Blob([view], { type: 'audio/wav' });
}

function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}

function floatTo16BitPCM(output, offset, input) {
    for (let i = 0; i < input.length; i++, offset += 2) {
        const s = Math.max(-1, Math.min(1, input[i]));
        output.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
}

async function decodeBlob(blob, fileName = '') {
    decodeOutput.textContent = "";
    copyDecodedBtn.style.display = 'none';
    decodeSpinner.style.display = 'inline-block';
    decodeOutput.textContent = "Decoding message...";
    recordBtn.disabled = true;
    decodeBtn.disabled = true;

    try {
        const formData = new FormData();
        // The backend expects a file with a name.
        formData.append("file", blob, "live_recording.wav");

        const res = await fetch(`${API_BASE}/decode_signal`, {
            method: "POST",
            body: formData
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || `HTTP Error ${res.status}`);
        }

        const data = await res.json();
        if (data.decoded_text) {
            decodeOutput.innerHTML = `<span class="status-success">Decoded Message:</span><br>${data.decoded_text}`;
            if (data.detected_mode) {
                decodedModeDisplay.textContent = `(Mode: ${data.detected_mode})`;
            } else {
                decodedModeDisplay.textContent = '';
            }
            copyDecodedBtn.style.display = 'block';
        } else {
            decodeOutput.innerHTML = `<span class="status-error">No message decoded.</span>`;
            decodedModeDisplay.textContent = '';
        }
    } catch (e) {
        decodeOutput.innerHTML = `<span class="status-error">Error decoding: ${e.message}</span>`;
    } finally {
        decodeSpinner.style.display = 'none';
        recordBtn.disabled = false;
        decodeBtn.disabled = false;
    }
}

// Decode from File
decodeBtn.onclick = async () => {
    const file = fileInput.files[0];
    if (!file) {
        decodeOutput.innerHTML = `<span class="status-error">Error: Please select an audio file (.wav)!</span>`;
        return;
    }
    decodeBlob(file, file.name);
};

// Live Recording Logic
recordBtn.onclick = async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks);
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();

            try {
                const arrayBuffer = await audioBlob.arrayBuffer();
                const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
                const wavBlob = encodeWAV(audioBuffer);
                decodeBlob(wavBlob, 'live_recording.wav');
            } catch (e) {
                console.error("Error decoding audio data:", e);
                recordStatus.textContent = `Error processing audio: ${e.message}`;
            } finally {
                // Clean up
                audioChunks = [];
                stream.getTracks().forEach(track => track.stop());
            }
        };

        // UI updates for recording state
        recordBtn.style.display = 'none';
        stopBtn.style.display = 'inline-block';
        recordStatus.textContent = "Recording...";
        decodeOutput.textContent = ""; // Clear previous output

        mediaRecorder.start();

    } catch (err) {
        recordStatus.textContent = `Error: ${err.message}`;
        console.error("Error accessing microphone:", err);
    }
};

stopBtn.onclick = () => {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        // UI updates
        recordBtn.style.display = 'inline-block';
        stopBtn.style.display = 'none';
        recordStatus.textContent = "";
    }
};

// Copy decoded text to clipboard
copyDecodedBtn.onclick = async () => {
  try {
    // Get only the text content, excluding the status span
    const textToCopy = decodeOutput.textContent.replace('Decoded Message:', '').trim();
    await navigator.clipboard.writeText(textToCopy);
    alert('Decoded text copied to clipboard!');
  } catch (err) {
    console.error('Error copying text: ', err);
    alert('Error copying text.');
  }
};
