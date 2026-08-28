@echo off
REM EMOS Virtual Environment Setup Script for Windows
REM Creates a Python virtual environment and installs dependencies from requirements.txt

setlocal enabledelayedexpansion

cls
echo ==================================================
echo EMOS Virtual Environment Setup
echo ==================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python found: %PYTHON_VERSION%
echo.

REM Create virtual environment
set VENV_DIR=emos_env
echo Creating virtual environment: %VENV_DIR%

if exist "%VENV_DIR%" (
    echo.
    echo Virtual environment already exists at: %VENV_DIR%
    set /p RECREATE="Do you want to recreate it? (y/n): "
    if /i "!RECREATE!"=="y" (
        rmdir /s /q "%VENV_DIR%"
        echo Removed existing environment
    ) else (
        echo Using existing environment
    )
)

if not exist "%VENV_DIR%" (
    python -m venv "%VENV_DIR%"
    echo Virtual environment created: %VENV_DIR%
) else (
    echo Virtual environment already exists
)

echo.
echo Installing dependencies from requirements.txt...

REM Install dependencies
call "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel >nul 2>&1
call "%VENV_DIR%\Scripts\pip.exe" install -r requirements.txt

echo.
echo ==================================================
echo Setup Complete!
echo ==================================================
echo.
echo To activate the virtual environment, run:
echo.
echo   %VENV_DIR%\Scripts\activate.bat
echo.
echo To deactivate later, run:
echo.
echo   deactivate
echo.
echo ==================================================
pause
