#!/bin/bash

# Define the path to the virtual environment (relative to this script)
VENV_PATH="$(dirname "$0")/../.venv"

# Check if the virtual environment exists, then activate it
if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
else
    echo "Virtual environment not found at $VENV_PATH. Please create it and install Flask."
    exit 1
fi

# Set the Flask app environment variable to an absolute path
export FLASK_APP="$(dirname "$0")/pyfitsserver/server.py"

# Run the Flask server
flask run --host=127.0.0.1 --port=5000