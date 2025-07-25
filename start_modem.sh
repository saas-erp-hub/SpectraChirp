#!/bin/bash

# Change to the script's directory to ensure correct relative paths
cd "$(dirname "$0")"

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
