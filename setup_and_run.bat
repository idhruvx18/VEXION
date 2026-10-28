@echo off
title VEXION Setup
color 0B
echo.
echo  ██╗   ██╗███████╗██╗  ██╗██╗ ██████╗ ███╗   ██╗
echo  ██║   ██║██╔════╝╚██╗██╔╝██║██╔═══██╗████╗  ██║
echo  ██║   ██║█████╗   ╚███╔╝ ██║██║   ██║██╔██╗ ██║
echo  ╚██╗ ██╔╝██╔══╝   ██╔██╗ ██║██║   ██║██║╚██╗██║
echo   ╚████╔╝ ███████╗██╔╝ ██╗██║╚██████╔╝██║ ╚████║
echo    ╚═══╝  ╚══════╝╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝
echo.
echo  THINK. EXECUTE. VERIFY.
echo  ─────────────────────────────────────────────────
echo.

:: ── Check Python ────────────────────────────────────────────────────────────
echo [1/5] Checking Python version...
py --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python not found.
    echo  Download Python 3.11+ from https://www.python.org/downloads/
    echo  Make sure to tick "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('py --version 2^>^&1') do set PYVER=%%v
echo  Python %PYVER% found.

:: ── Virtual environment ──────────────────────────────────────────────────────
echo.
echo [2/5] Checking virtual environment...
if not exist "venv\Scripts\activate.bat" (
    echo  Creating virtual environment...
    py -m venv venv
    if errorlevel 1 (
        echo.
        echo  ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  Virtual environment created.
) else (
    echo  Virtual environment already exists.
)

:: ── Dependencies ─────────────────────────────────────────────────────────────
echo.
echo [3/5] Installing / verifying dependencies...
call venv\Scripts\pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo  ERROR: Dependency installation failed.
    echo  Check your internet connection and try again.
    echo  You can also run manually:
    echo    venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
echo  Dependencies OK.

:: ── .env file ────────────────────────────────────────────────────────────────
echo.
echo [4/5] Checking configuration...
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo  Created .env from .env.example.
    echo.
    echo  *** ACTION REQUIRED ***
    echo  Open .env in a text editor and fill in your API keys:
    echo    - GEMINI_API_KEY      (optional, for cloud AI)
    echo    - ELEVENLABS_API_KEY  (optional, for voice output)
    echo    - ELEVENLABS_VOICE_ID (required for ElevenLabs voice)
    echo    - OLLAMA_MODEL        (check with: ollama list)
    echo.
    echo  VEXION will still launch in limited mode without keys.
    echo.
) else (
    echo  .env file found.
)

:: ── Launch ───────────────────────────────────────────────────────────────────
echo.
echo [5/5] Starting VEXION...
echo  Press Ctrl+C to stop. Press Escape in the app to exit full-screen.
echo.
call venv\Scripts\python main.py %*
if errorlevel 1 (
    echo.
    echo  VEXION exited with an error.
    echo  Run with --diagnostics to check configuration:
    echo    venv\Scripts\python main.py --diagnostics
    echo.
    pause
)
