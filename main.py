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

MODEL = os.getenv("MIRA_MODEL", "groq/compound")
MAX_HISTORY = 4
MAX_MEMORY_ITEMS = 4
MAX_CONTEXT_CHARS = 8000
api_key = os.getenv("GROQ_API_KEY")

app = FastAPI(title="MIRA", version="2.9")
origins = [x.strip() for x in os.getenv("MIRA_ALLOWED_ORIGINS", "").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions = defaultdict(lambda: deque(maxlen=MAX_HISTORY))

try:
    init_memory()
    MEMORY_STATUS = "ready"
except Exception:
    MEMORY_STATUS = "fallback"

SYSTEM_PROMPT = """
Tum MIRA ho, Boss ki personal AI assistant.

PERSONALITY:
- Boss ko hamesha exactly "Boss" kehkar bulao. "Bossa", "Boss ji" ya nickname mat banao.
- Tum female assistant ho. Natural feminine forms use karo.
- Roman Hindi + natural Indian English/Hinglish mein baat karo.
- Devanagari Hindi mat use karo jab tak Boss specifically na kahe.
- Smart, calm, friendly aur confident tone rakho.
- Simple question ka simple answer do.

ACCURACY:
- Facts invent mat karo.
- Current/latest/today/price/rate/news/weather/availability/result ke liye live web tools use karo.
- Live verification na ho to guess mat karo.
- Exact price, date, timing, address, availability ya specification assume mat karo.

MEMORY:
- Relevant long-term memory ko context ke liye use karo.
- Clearly requested memory ko save karo.
- Passwords, OTPs, API keys, secrets, tokens, CVV, card numbers, bank credentials, medical details ko automatic memory mein save mat karo.

TOOLS:
- Safe local tools: calculator, current_time, list_files, read_file, search_files, write_note.
- File tools sirf MIRA workspace ke andar kaam karte hain.
- Arbitrary shell commands, destructive actions, credential access, ya security bypass mat karo.
- Current information ke liye Groq Compound ke built-in live web capabilities use karo.
""".strip()


def build_messages(session_id: str, user_message: str):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    memories = list_memories(session_id, MAX_MEMORY_ITEMS)
    if memories:
        lines = []
        for m in memories:
            value = str(m.get("value", ""))[:400]
            lines.append(f"- [{m.get('category', 'general')}] {m.get('key', '')}: {value}")
        messages.append({"role": "system", "content": "Saved memory:\n" + "\n".join(lines)})

    for item in list(sessions[session_id]):
        content = str(item.get("content", ""))[:700]
        if content:
            messages.append({"role": item.get("role", "user"), "content": content})

    messages.append({"role": "user", "content": user_message[:2000]})

    total = sum(len(str(m.get("content", ""))) for m in messages)
    while total > MAX_CONTEXT_CHARS and len(messages) > 2:
        removed = messages.pop(1)
        total -= len(str(removed.get("content", "")))
    return messages


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
    try:
        return client.chat.completions.create(
            model=MODEL,
            messages=messages,
            search_settings={"country": "india"},
        )
    except Exception as first_error:
        print(f"MIRA Compound request failed: {type(first_error).__name__}: {first_error}", flush=True)
        raise first_error


@app.get("/")
def home():
    return {
        "assistant":"MIRA", "status":"ONLINE", "version":"2.9", "model":MODEL,
        "memory":MEMORY_STATUS,
        "tools":["web_search","visit_website","code_execution","wolfram_alpha","calculator","current_time","list_files","read_file","search_files","write_note"],
        "message":"Boss, MIRA online hai."
    }


@app.get("/health")
def health():
    return {"status":"ok", "assistant":"MIRA", "model":MODEL, "memory":MEMORY_STATUS, "version":"2.9", "groq_configured":bool(api_key)}


@app.get("/tools")
def tools():
    return {"assistant":"MIRA", "safe_tools":[
        {"name":"calculator","permission":"READ"},
        {"name":"current_time","permission":"READ"},
        {"name":"list_files","permission":"READ"},
        {"name":"read_file","permission":"READ"},
        {"name":"search_files","permission":"READ"},
        {"name":"write_note","permission":"WRITE"},
    ], "dangerous_shell":"DENIED"}


@app.post("/tool")
def tool(name: str = Query(..., min_length=1, max_length=50), expression: str = Query("", max_length=1000), filename: str = Query("", max_length=500), content: str = Query("", max_length=50000), query: str = Query("", max_length=500)):
    try:
        if name == "calculator":
            return run_tool(name, expression=expression)
        if name == "read_file":
            return run_tool(name, filename=filename)
        if name == "write_note":
            return run_tool(name, filename=filename, content=content)
        if name == "search_files":
            return run_tool(name, query=query)
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
