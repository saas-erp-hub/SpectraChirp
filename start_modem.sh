#!/bin/bash

# Function to kill processes using a given port
kill_process_on_port() {
    PORT=$1
    echo "Checking for processes on port $PORT..."
    # Find PIDs using the port, filter for LISTEN state, and extract PID
    PIDS=$(lsof -t -i :$PORT -sTCP:LISTEN)
    if [ -n "$PIDS" ]; then
        echo "Found processes on port $PORT: $PIDS. Killing them..."
        kill -9 $PIDS
        echo "Processes on port $PORT killed."
    else
        echo "No processes found on port $PORT."
    fi
}

# Change to the script's directory to ensure correct relative paths
cd "$(dirname "$0")"

# Kill any existing processes on port 8001 (backend)
kill_process_on_port 8001

# Kill any existing processes on port 8000 (frontend)
kill_process_on_port 8000

# Start the backend server in the background
python -m backend &

# Wait a few seconds for the backend server to start
sleep 3

# Start the frontend HTTP server in the background
(cd frontend && python -m http.server 8000) &

# Wait a few seconds for the frontend server to start
sleep 2

# Open the frontend in the default web browser
xdg-open http://localhost:8000/index.html 2>/dev/null || open http://localhost:8000/index.html 2>/dev/null || echo "Please open http://localhost:8000/index.html in your browser."