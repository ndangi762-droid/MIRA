@echo off
cd /d "%~dp0.."
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "pc_agent\mira_pc_agent.py"
) else (
  python "pc_agent\mira_pc_agent.py"
)
pause
