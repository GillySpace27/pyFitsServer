#!/bin/bash

# Find the process IDs (PIDs) of the Flask server running on port 5000
FLASK_PIDS=$(lsof -ti:5000)

if [ -n "$FLASK_PIDS" ]; then
    # Iterate over each PID and kill it
    for PID in $FLASK_PIDS; do
        kill "$PID"
        # echo "Stopped Flask server (PID: $PID)"
    done
else
    echo "No Flask server running on port 5000"
fi