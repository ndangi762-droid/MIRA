import os
from dotenv import load_dotenv

load_dotenv()

MIRA_NAME = os.getenv("MIRA_NAME", "MIRA")
USER_NAME = os.getenv("MIRA_USER_NAME", "Boss")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
MEMORY_DB = os.getenv("MEMORY_DB", "data/mira.db")
