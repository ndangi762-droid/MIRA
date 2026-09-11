from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from dotenv import load_dotenv
import os
from collections import defaultdict, deque
from memory import init_memory, save_memory, list_memories, delete_memory
from tools import run_tool

load_dotenv("backend/.env")
load_dotenv()

# Compound Mini is designed for lower-latency tool use and keeps the live-web
# request path lightweight. It still supports built-in web search.
MODEL = os.getenv("MIRA_MODEL", "groq/compound-mini")
MAX_HISTORY = 2
MAX_MEMORY_ITEMS = 2
api_key = os.getenv("GROQ_API_KEY")

app = FastAPI(title="MIRA", version="3.0")
origins = [x.strip() for x in os.getenv("MIRA_ALLOWED_ORIGINS", "").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins or ["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
sessions = defaultdict(lambda: deque(maxlen=MAX_HISTORY))

try:
    init_memory()
    MEMORY_STATUS = "ready"
except Exception:
    MEMORY_STATUS = "fallback"

SYSTEM_PROMPT = """
Tum MIRA ho, Boss ki personal AI assistant.
- Boss ko hamesha exactly Boss kehkar bulao. Bossa ya Boss ji mat bolo.
- Roman Hindi + natural Indian English/Hinglish mein baat karo.
- Devanagari mat use karo jab tak Boss specifically na kahe.
- Smart, calm, friendly aur concise raho.
- Facts invent mat karo.
- Current/latest/today/news/price/rate/weather/availability ke liye live web search use karo.
- Live verification na ho to guess mat karo.
- Relevant saved memory use karo, lekin secrets, OTPs, API keys, passwords, tokens, CVV, bank credentials ya medical details automatic memory mein save mat karo.
- Safe local tools available hain: calculator, current_time, list_files, read_file, search_files, write_note.
""".strip()


def build_messages(session_id: str, user_message: str):
    # For Compound's live-web path, deliberately send only the essential prompt
    # and current question. This prevents accumulated memory/history from ever
    # causing an upstream request-size failure.
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message[:2000]},
    ]


def extract_tool_info(message):
    tools = getattr(message, "executed_tools", None) or []
    return bool(tools)


def explicit_memory(text: str):
    lowered = text.lower().strip()
    triggers = ["yaad rakho", "yaad rakhna", "remember this", "save this", "memory me save", "memory mein save"]
    for trigger in triggers:
        idx = lowered.find(trigger)
        if idx >= 0:
            cleaned = text[idx + len(trigger):].strip(" :-,.")
            return cleaned if cleaned else None
    return None


def auto_memory_candidate(text: str):
    low = text.lower().strip()
    blocked = ["password", "passcode", "otp", "api key", "apikey", "secret", "token", "cvv", "card number", "bank account", "medical", "medicine", "diagnosis"]
    if any(x in low for x in blocked):
        return None
    patterns = [
        ("preference", ["mujhe pasand hai", "mujhe pasand", "i prefer", "i like", "i don't like", "mujhe nahi pasand"]),
        ("instruction", ["hamesha", "always", "default me", "default mein", "aage se", "from now on"]),
        ("project", ["mera project", "hamara project", "my project", "mira ko", "mira mein"]),
        ("workflow", ["main use karta hoon", "main use karti hoon", "i use", "mera workflow", "my workflow"]),
    ]
    for category, triggers in patterns:
        if any(t in low for t in triggers) and len(text) <= 600:
            return category, text.strip()
    return None


def save_memory_from_message(session_id: str, text: str):
    explicit = explicit_memory(text)
    if explicit:
        key = "explicit_" + str(abs(hash(explicit)) % 100000000)
        save_memory(session_id, key, explicit, "explicit")
        return {"saved": True, "type": "explicit", "key": key}
    candidate = auto_memory_candidate(text)
    if candidate:
        category, value = candidate
        key = category + "_" + str(abs(hash(value)) % 100000000)
        save_memory(session_id, key, value, category)
        return {"saved": True, "type": "automatic", "key": key}
    return {"saved": False}


def call_compound(client, messages):
    # Do not add search_settings here. Compound decides when web search is
    # appropriate, and the smallest possible request is the most reliable path.
    return client.chat.completions.create(model=MODEL, messages=messages)


@app.get("/")
def home():
    return {"assistant":"MIRA", "status":"ONLINE", "version":"3.0", "model":MODEL, "memory":MEMORY_STATUS, "tools":["web_search","visit_website","code_execution","wolfram_alpha","calculator","current_time","list_files","read_file","search_files","write_note"], "message":"Boss, MIRA online hai."}


@app.get("/health")
def health():
    return {"status":"ok", "assistant":"MIRA", "model":MODEL, "memory":MEMORY_STATUS, "version":"3.0", "groq_configured":bool(api_key)}


@app.get("/tools")
def tools():
    return {"assistant":"MIRA", "safe_tools":[{"name":"calculator","permission":"READ"},{"name":"current_time","permission":"READ"},{"name":"list_files","permission":"READ"},{"name":"read_file","permission":"READ"},{"name":"search_files","permission":"READ"},{"name":"write_note","permission":"WRITE"}], "dangerous_shell":"DENIED"}


@app.post("/tool")
def tool(name: str = Query(..., min_length=1, max_length=50), expression: str = Query("", max_length=1000), filename: str = Query("", max_length=500), content: str = Query("", max_length=50000), query: str = Query("", max_length=500)):
    try:
        if name == "calculator": return run_tool(name, expression=expression)
        if name == "read_file": return run_tool(name, filename=filename)
        if name == "write_note": return run_tool(name, filename=filename, content=content)
        if name == "search_files": return run_tool(name, query=query)
        return run_tool(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found in MIRA workspace")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Tool error: {type(exc).__name__}") from exc


@app.get("/ask")
def ask(message: str = Query(..., min_length=1, max_length=12000), session_id: str = Query("boss", min_length=1, max_length=100)):
    if not api_key:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY is not configured")
    try:
        memory_result = save_memory_from_message(session_id, message)
        client = Groq(api_key=api_key, default_headers={"Groq-Model-Version":"latest"})
        response = call_compound(client, build_messages(session_id, message))
        assistant_message = response.choices[0].message
        answer = assistant_message.content or "Boss, mujhe is request ka clear answer nahi mila."
        sessions[session_id].append({"role":"user", "content":message})
        sessions[session_id].append({"role":"assistant", "content":answer})
        return {"assistant":"MIRA", "response":answer, "model":MODEL, "memory":MEMORY_STATUS, "memory_action":memory_result, "live_tools_used":extract_tool_info(assistant_message)}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"MIRA /ask failed: {type(exc).__name__}: {exc}", flush=True)
        raise HTTPException(status_code=502, detail=f"MIRA backend error: {type(exc).__name__}") from exc


@app.get("/memory")
def get_memory(session_id: str = Query("boss", min_length=1, max_length=100)):
    return {"assistant":"MIRA", "session_id":session_id, "memories":list_memories(session_id, 100)}


@app.post("/memory/save")
def memory_save(key: str = Query(..., min_length=1, max_length=100), value: str = Query(..., min_length=1, max_length=5000), category: str = Query("general", min_length=1, max_length=50), session_id: str = Query("boss", min_length=1, max_length=100)):
    try:
        save_memory(session_id, key.strip(), value.strip(), category.strip())
        return {"assistant":"MIRA", "status":"saved", "key":key.strip(), "category":category.strip()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Memory error: {type(exc).__name__}") from exc


@app.delete("/memory")
def memory_delete(key: str = Query(..., min_length=1, max_length=100), session_id: str = Query("boss", min_length=1, max_length=100)):
    try:
        delete_memory(session_id, key.strip())
        return {"assistant":"MIRA", "status":"deleted", "key":key.strip()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Memory error: {type(exc).__name__}") from exc


@app.post("/reset")
def reset(session_id: str = Query("boss", min_length=1, max_length=100)):
    sessions.pop(session_id, None)
    return {"assistant":"MIRA", "status":"reset", "session_id":session_id}
