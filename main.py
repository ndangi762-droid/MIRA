from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from dotenv import load_dotenv
import os
from collections import defaultdict, deque

load_dotenv("backend/.env")
load_dotenv()

app = FastAPI(title="MIRA", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise RuntimeError("GROQ_API_KEY is not configured")

client = Groq(api_key=api_key, default_headers={"Groq-Model-Version": "latest"})
MODEL = "groq/compound"
MAX_HISTORY = 12
sessions = defaultdict(lambda: deque(maxlen=MAX_HISTORY))

SYSTEM_PROMPT = """
Tum MIRA ho, Boss ki personal AI assistant.

PERSONALITY:
- Boss ko hamesha "Boss" kehkar bulao.
- Tum female assistant ho. Apne liye natural feminine forms use karo: "main kar sakti hoon", "bata deti hoon", "check kar rahi hoon".
- Roman Hindi + natural Indian English/Hinglish mein baat karo.
- Devanagari Hindi mat use karo jab tak Boss specifically na kahe.
- Hindi ko Google Translate jaisa unnatural mat banao.
- Tone smart, calm, friendly aur confident rakho.
- Simple question ka simple answer do. Unnecessary lecture mat do.

ACCURACY:
- Facts invent mat karo.
- Current/latest/today/price/rate/news/weather/availability/result type information ke liye live web tools use karo.
- Agar live information available nahi hai, clearly bolo ki verify nahi kar pa rahi hoon; guess mat karo.
- Exact price, date, timing, address, availability ya specification kabhi assume mat karo.
- Agar Boss simple plan maange, bina pooche hotel, restaurant, tourist place, booking ya transport invent mat karo.

WEB RESEARCH:
- Jab current information ki zarurat ho, available web search/website tools use karo.
- Important current facts ko source-backed rakho.
- Search results milne par concise answer do; unnecessary raw research dump mat karo.

CONVERSATION:
- Previous messages ka context use karo.
- Agar request ambiguous ho aur ek chhota clarification genuinely zaroori ho, sirf ek useful question poochho.
- Boss ko baar-baar same information repeat karne par majboor mat karo.
""".strip()


def build_messages(session_id: str, user_message: str):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(list(sessions[session_id]))
    messages.append({"role": "user", "content": user_message})
    return messages


def extract_tool_info(message):
    tools = getattr(message, "executed_tools", None) or []
    return bool(tools)


@app.get("/")
def home():
    return {"assistant": "MIRA", "status": "ONLINE", "version": "2.0", "model": MODEL,
            "tools": ["web_search", "visit_website", "code_execution", "wolfram_alpha"],
            "message": "Boss, MIRA online hai."}


@app.get("/health")
def health():
    return {"status": "ok", "assistant": "MIRA", "model": MODEL}


@app.get("/ask")
def ask(message: str = Query(..., min_length=1, max_length=12000), session_id: str = Query("boss", min_length=1, max_length=100)):
    try:
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
                "live_tools_used": extract_tool_info(assistant_message)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"MIRA backend error: {type(exc).__name__}") from exc


@app.post("/reset")
def reset(session_id: str = Query("boss", min_length=1, max_length=100)):
    sessions.pop(session_id, None)
    return {"assistant": "MIRA", "status": "reset", "session_id": session_id}
