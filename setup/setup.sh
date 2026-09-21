#!/bin/bash

# EMOS Virtual Environment Setup Script
# Creates a Python virtual environment and installs dependencies from requirements.txt

set -e  # Exit on error

echo "=================================================="
echo "EMOS Virtual Environment Setup"
echo "=================================================="
echo ""

# Use an explicitly requested interpreter, otherwise choose the first python3
# outside Conda installations found on PATH.
if [[ -n "${EMOS_PYTHON:-}" ]]; then
    PYTHON_BIN="$EMOS_PYTHON"
elif [[ -x /usr/bin/python3 ]]; then
    PYTHON_BIN=/usr/bin/python3
else
    PYTHON_BIN=$(type -a -p python3 | grep -Ev '/(mini|ana)conda/' | head -n 1 || true)
fi

if [ -z "$PYTHON_BIN" ] || [ ! -x "$PYTHON_BIN" ]; then
    echo "Error: a non-Conda Python 3 interpreter was not found"
    echo "Install Python 3 with venv support, or set EMOS_PYTHON to its full path."
    exit 1
fi

if ! "$PYTHON_BIN" -m ensurepip --version > /dev/null 2>&1; then
    echo "Error: $PYTHON_BIN does not include ensurepip/venv support"
    echo "On Ubuntu/Debian, install it with: sudo apt install python3-venv"
    exit 1
fi

PYTHON_VERSION=$("$PYTHON_BIN" --version 2>&1 | awk '{print $2}')
echo "Python found: $PYTHON_VERSION ($PYTHON_BIN)"
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
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    echo "✓ Virtual environment created: $VENV_DIR"
else
    echo "✓ Virtual environment already exists"
fi

echo ""
echo "Installing dependencies from requirements.txt..."

# Install dependencies
"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel > /dev/null 2>&1
"$VENV_DIR/bin/pip" install --prefer-binary -r requirements.txt

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
