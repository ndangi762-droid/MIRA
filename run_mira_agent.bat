@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Creating MIRA Agent environment...
  py -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  python -m pip install fastapi "uvicorn[standard]"
) else (
  call .venv\Scripts\activate.bat
)
if "%MIRA_AGENT_TOKEN%"=="" (
  echo.
  echo Set MIRA_AGENT_TOKEN before production use.
  echo Example: set MIRA_AGENT_TOKEN=YOUR_LONG_RANDOM_TOKEN
  echo.
)
python -m uvicorn mira_agent:app --host 127.0.0.1 --port 8765
pause
