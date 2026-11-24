@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==========================================
echo   VoiceInput - install dependencies
echo ==========================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [1/2] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo ERROR: failed to create venv. Make sure Python is installed.
        pause
        exit /b 1
    )
) else (
    echo [1/2] venv already exists.
)

echo [2/2] Installing packages (may take a few minutes)...
"venv\Scripts\python.exe" -m pip install --upgrade pip
"venv\Scripts\python.exe" -m pip install sherpa-onnx sounddevice numpy pynput pyperclip

if errorlevel 1 (
    echo.
    echo ERROR: install failed. Check your internet connection and retry.
) else (
    echo.
    echo Done! Now double-click "启动语音输入.bat" to start.
)
echo.
pause
