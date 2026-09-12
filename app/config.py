import os
from dotenv import load_dotenv

load_dotenv()

MIRA_NAME = os.getenv("MIRA_NAME", "MIRA")
USER_NAME = os.getenv("MIRA_USER_NAME", "Boss")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")
PIPER_VOICE = os.getenv("PIPER_VOICE", "hi_IN-priyamvada-medium")
PIPER_MODEL_PATH = os.getenv("PIPER_MODEL_PATH", "models/piper/hi_IN-priyamvada-medium.onnx")
PIPER_BINARY = os.getenv("PIPER_BINARY", "piper")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
MEMORY_DB = os.getenv("MEMORY_DB", "data/mira.db")
