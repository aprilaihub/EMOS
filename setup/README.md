# EMOS Virtual Environment Setup

This directory contains scripts to easily set up a Python virtual environment and install dependencies.

## Quick Start

### On macOS/Linux:
```bash
bash setup/setup.sh
source emos_env/bin/activate
```

### On Windows:
```cmd
setup\setup.bat
emos_env\Scripts\activate.bat
```

## What the Scripts Do

1. Check if Python 3 is installed
2. Create a virtual environment named `emos_env`
3. Install all dependencies from `requirements.txt`
4. Print activation instructions

## Manual Setup (if you prefer)

If you prefer to set up manually:

```bash
# Create virtual environment
python3 -m venv emos_env

# Activate it
source emos_env/bin/activate  # macOS/Linux
# or
emos_env\Scripts\activate.bat  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Why Use a Virtual Environment?

- **Isolation**: Keep project dependencies separate from system Python
- **Reproducibility**: Exact version control of all packages
- **Clean uninstall**: Delete `emos_env` folder to remove everything

## Adding New Dependencies

**⭐ Always add libraries to `requirements.txt`** - This keeps all dependencies in one place and ensures everyone uses the same versions.

1. Add your library to `requirements.txt` with the desired version:
   ```
   library_name==1.0.0
   ```

2. Install it in your virtual environment:
   ```bash
   pip install library_name==1.0.0
   ```

3. Share the updated `requirements.txt` within your PR

**Why this approach?**
- All dependencies centralized in one file
- Version consistency across all developers
- Easy to reproduce environment on any machine
- New developers run one setup command and get everything

