from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from dotenv import load_dotenv
import os
from collections import defaultdict, deque
from memory import init_memory, save_memory, list_memories, delete_memory

load_dotenv("backend/.env")
load_dotenv()

app = FastAPI(title="MIRA", version="2.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise RuntimeError("GROQ_API_KEY is not configured")

client = Groq(api_key=api_key, default_headers={"Groq-Model-Version": "latest"})
MODEL = "groq/compound"
MAX_HISTORY = 12
sessions = defaultdict(lambda: deque(maxlen=MAX_HISTORY))

try:
    init_memory()
    MEMORY_STATUS = "ready"
except Exception:
    MEMORY_STATUS = "fallback"

SYSTEM_PROMPT = """
Tum MIRA ho, Boss ki personal AI assistant.

PERSONALITY:
- Boss ko hamesha "Boss" kehkar bulao.
- Tum female assistant ho. Natural feminine forms use karo: "main kar sakti hoon", "bata deti hoon".
- Roman Hindi + natural Indian English/Hinglish mein baat karo.
- Devanagari Hindi mat use karo jab tak Boss specifically na kahe.
- Hindi ko Google Translate jaisa unnatural mat banao.
- Smart, calm, friendly aur confident tone rakho.
- Simple question ka simple answer do.

ACCURACY:
- Facts invent mat karo.
- Current/latest/today/price/rate/news/weather/availability/result ke liye live web tools use karo.
- Live verification na ho to guess mat karo.
- Exact price, date, timing, address, availability ya specification assume mat karo.
- Simple plan mein bina pooche hotel, restaurant, tourist place, booking ya transport invent mat karo.

MEMORY:
- Long-term memory available hai. Relevant saved memories ko context samjho.
- Boss jab clearly bole "yaad rakho", "remember this", "save this", tab memory save karne ki koshish karo.
- Temporary ya sensitive information ko bina clear request ke memory mein save mat karo.
- Agar memory save nahi ho paaye to honestly batao.
- Purani memory ko current user message se override karna ho to latest explicit instruction follow karo.

CONVERSATION:
- Previous messages ka context use karo.
- Ambiguous request mein sirf ek useful clarification poochho.
- Boss ko same information baar-baar repeat karne par majboor mat karo.
""".strip()


def build_messages(session_id: str, user_message: str):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    memories = list_memories(session_id, 30)
    if memories:
        memory_text = "\n".join(f"- {m['key']}: {m['value']}" for m in memories)
        messages.append({"role": "system", "content": "Saved long-term memories for this Boss:\n" + memory_text})
    messages.extend(list(sessions[session_id]))
    messages.append({"role": "user", "content": user_message})
    return messages


def extract_tool_info(message):
    return bool(getattr(message, "executed_tools", None) or [])


def maybe_save_explicit_memory(session_id: str, text: str):
    lowered = text.lower().strip()
    triggers = ["yaad rakho", "yaad rakhna", "remember this", "save this", "memory me save", "memory mein save"]
    if not any(t in lowered for t in triggers):
        return None
    cleaned = text
    for trigger in triggers:
        idx = lowered.find(trigger)
        if idx >= 0:
            cleaned = text[idx + len(trigger):].strip(" :-,.")
            break
    if not cleaned:
        return None
    key = "memory_" + str(abs(hash(cleaned)) % 100000000)
    save_memory(session_id, key, cleaned)
    return key


@app.get("/")
def home():
    return {"assistant": "MIRA", "status": "ONLINE", "version": "2.1", "model": MODEL,
            "memory": MEMORY_STATUS,
            "tools": ["web_search", "visit_website", "code_execution", "wolfram_alpha"],
            "message": "Boss, MIRA online hai."}


@app.get("/health")
def health():
    return {"status": "ok", "assistant": "MIRA", "model": MODEL, "memory": MEMORY_STATUS}


@app.get("/ask")
def ask(message: str = Query(..., min_length=1, max_length=12000), session_id: str = Query("boss", min_length=1, max_length=100)):
    try:
        maybe_save_explicit_memory(session_id, message)
        response = client.chat.completions.create(
            model=MODEL,
            messages=build_messages(session_id, message),
            compound_custom={"tools": {"enabled_tools": ["web_search", "visit_website", "code_interpreter", "wolfram_alpha"]}},
        )
        assistant_message = response.choices[0].message
        answer = assistant_message.content or "Boss, mujhe is request ka clear answer nahi mila."
        sessions[session_id].append({"role": "user", "content": message})
        sessions[session_id].append({"role": "assistant", "content": answer})
        return {"assistant": "MIRA", "response": answer, "model": MODEL,
                "memory": MEMORY_STATUS, "live_tools_used": extract_tool_info(assistant_message)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"MIRA backend error: {type(exc).__name__}") from exc


@app.get("/memory")
def get_memory(session_id: str = Query("boss", min_length=1, max_length=100)):
    return {"assistant": "MIRA", "session_id": session_id, "memories": list_memories(session_id, 100)}


@app.post("/memory/save")
def memory_save(key: str = Query(..., min_length=1, max_length=100), value: str = Query(..., min_length=1, max_length=5000), session_id: str = Query("boss", min_length=1, max_length=100)):
    try:
        save_memory(session_id, key.strip(), value.strip())
        return {"assistant": "MIRA", "status": "saved", "key": key.strip()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Memory error: {type(exc).__name__}") from exc


@app.delete("/memory")
def memory_delete(key: str = Query(..., min_length=1, max_length=100), session_id: str = Query("boss", min_length=1, max_length=100)):
    try:
        delete_memory(session_id, key.strip())
        return {"assistant": "MIRA", "status": "deleted", "key": key.strip()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Memory error: {type(exc).__name__}") from exc


@app.post("/reset")
def reset(session_id: str = Query("boss", min_length=1, max_length=100)):
    sessions.pop(session_id, None)
    return {"assistant": "MIRA", "status": "reset", "session_id": session_id}
