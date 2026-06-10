@echo off
REM TWC offline demo - Windows launcher (for local testing)
cd /d "%~dp0"
echo Checking Ollama...
curl -s http://localhost:11434/api/version >nul 2>&1
if errorlevel 1 (
  echo Ollama is not running. Starting it...
  start "" ollama serve
  timeout /t 4 /nobreak >nul
)
python server.py
pause
