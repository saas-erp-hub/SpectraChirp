#!/bin/bash

# Pfad zum Projekt-Stammverzeichnis
PROJECT_ROOT="$(dirname "$0")"

echo "Starting FastAPI backend..."
# Startet den FastAPI-Server im Hintergrund
# uv run uvicorn backend.main:app --reload &
# Startet den FastAPI-Server im Hintergrund
# Verwenden Sie `nohup` und `&` um den Prozess im Hintergrund zu halten, auch wenn das Terminal geschlossen wird.
# Die Ausgabe wird in nohup.out umgeleitet.
nohup uv run uvicorn backend.main:app --reload > "$PROJECT_ROOT/backend_startup.log" 2>&1 &
BACKEND_PID=$!
echo "FastAPI backend started with PID: $BACKEND_PID. Log: $PROJECT_ROOT/backend_startup.log"

echo "Waiting for backend to start (5 seconds)..."
sleep 5 # Gibt dem Backend Zeit zum Starten

echo "Opening frontend in browser..."
# Öffnet die index.html im Standardbrowser
# Plattformunabhängige Lösung
if command -v xdg-open > /dev/null; then
  xdg-open "$PROJECT_ROOT/frontend/index.html"
elif command -v open > /dev/null; then
  open "$PROJECT_ROOT/frontend/index.html"
elif command -v start > /dev/null; then
  start "$PROJECT_ROOT/frontend/index.html"
else
  echo "Could not open browser automatically. Please open $PROJECT_ROOT/frontend/index.html manually."
fi

echo "Modem startup script finished."
echo "To stop the backend, run: kill $BACKEND_PID"