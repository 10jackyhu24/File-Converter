@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [File Converter] Creating Python environment...
  python -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -c "import flask, PIL, pypdf, fitz" >nul 2>&1
if errorlevel 1 (
  echo [File Converter] Installing dependencies...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo.
    echo Could not install dependencies. Check your internet connection.
    pause
    exit /b 1
  )
)

where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo.
  echo WARNING: FFmpeg was not found in PATH. Video and audio features will not work.
  echo Install FFmpeg, then restart this file.
  echo.
)

python app.py
pause
