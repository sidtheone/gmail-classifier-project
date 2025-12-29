#!/bin/bash
# Wrapper script to run classifier with correct Python interpreter
# This avoids issues with shell aliases overriding the venv

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$SCRIPT_DIR/venv/bin/python"

# Check if venv exists
if [ ! -f "$PYTHON" ]; then
    echo "Error: Virtual environment not found at $SCRIPT_DIR/venv"
    echo "Please run: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Run the classifier with all passed arguments
"$PYTHON" "$SCRIPT_DIR/email_classifier.py" "$@"
