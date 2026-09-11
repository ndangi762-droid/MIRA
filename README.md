# MIRA v2

A local-first modular personal AI assistant.

## Stack
- Python + FastAPI
- Ollama local LLM
- SQLite conversation memory
- Simple web UI
- Modular tools layer

## Windows setup

```powershell
cd MIRA-v2
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m app.main
```

Open http://127.0.0.1:8000

Default Ollama model: qwen2.5:7b
Change it in .env.

Do not modify the project blindly. Analyze first, then implement changes incrementally.
