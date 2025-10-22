#!/bin/bash
set -e

# Create necessary directories
echo "Setting up directories..."
mkdir -p data logs

# Copy template .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.template .env
    echo "Please edit the .env file with your configuration"
else
    echo ".env file already exists, skipping..."
fi

# Install Python dependencies
echo "Installing Python dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete! Please edit the .env file with your configuration before running the script."
