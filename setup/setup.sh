#!/bin/bash

# EMOS Virtual Environment Setup Script
# Creates a Python virtual environment and installs dependencies from requirements.txt

set -e  # Exit on error

echo "=================================================="
echo "EMOS Virtual Environment Setup"
echo "=================================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python found: $PYTHON_VERSION"
echo ""

# Create virtual environment
VENV_DIR="emos_env"
echo "Creating virtual environment: $VENV_DIR"

if [ -d "$VENV_DIR" ]; then
    echo "⚠️  Virtual environment already exists at: $VENV_DIR"
    read -p "Do you want to recreate it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR"
        echo "Removed existing environment"
    else
        echo "Using existing environment"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created: $VENV_DIR"
else
    echo "✓ Virtual environment already exists"
fi

echo ""
echo "Installing dependencies from requirements.txt..."

# Install dependencies
"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel > /dev/null 2>&1
"$VENV_DIR/bin/pip" install -r requirements.txt

echo ""
echo "=================================================="
echo "✓ Setup Complete!"
echo "=================================================="
echo ""
echo "To activate the virtual environment, run:"
echo ""
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "To deactivate later, run:"
echo ""
echo "  deactivate"
echo ""
echo "=================================================="
