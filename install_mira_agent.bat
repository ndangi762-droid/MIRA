@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1 || (echo Python is required. & pause & exit /b 1)
py -m pip install fastapi uvicorn pydantic
if not defined MIRA_AGENT_TOKEN (
  echo.
  echo Set a persistent token before production use:
  echo   setx MIRA_AGENT_TOKEN "YOUR_LONG_RANDOM_TOKEN"
  echo Then open a new terminal and run this file again.
  echo.
)
py -m uvicorn mira_agent:app --host 127.0.0.1 --port 8765
pause
