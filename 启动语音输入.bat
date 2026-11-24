@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "venv\Scripts\pythonw.exe" (
    echo First run: installing dependencies...
    call "安装依赖.bat"
)

start "" "venv\Scripts\pythonw.exe" "voice_input.py"
