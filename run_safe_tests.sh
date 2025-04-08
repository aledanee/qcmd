#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "test_env" ]; then
    python3 -m venv test_env
fi

# Activate virtual environment
source test_env/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pytest requests

# Install package in development mode
pip install -e .

# Run safe tests only
echo "Running safe tests..."
python -m pytest tests/ -v -k "not (dangerous or process or timeout or execute or ssh)" "$@"

# Deactivate virtual environment
deactivate 