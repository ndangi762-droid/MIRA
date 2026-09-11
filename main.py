from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from dotenv import load_dotenv
import os
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from collections import defaultdict, deque
from memory import init_memory, save_memory, list_memories, delete_memory

load_dotenv("backend/.env")
load_dotenv()

MODEL = os.getenv("MIRA_MODEL", "openai/gpt-oss-20b")
MAX_HISTORY = 4
MAX_MEMORY_ITEMS = 4
api_key = os.getenv("GROQ_API_KEY")

app = FastAPI(title="MIRA", version="4.0")
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
- Roman Hindi + natural Indian English/Hinglish use karo. Devanagari mat use karo jab tak Boss specifically na kahe.
- Smart, calm, friendly aur concise raho.
- Facts invent mat karo. Agar web research context diya gaya hai to usi evidence ko use karo.
- Current/latest/today/news/price/rate/weather/result type questions ke liye supplied LIVE WEB SEARCH results ko priority do.
""".strip()

class SearchParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_result = False
        self.in_link = False
        self.in_snippet = False
        self.title = ""
        self.url = ""
        self.snippet = ""
        self.results = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        cls = attrs.get("class", "")
        if tag == "a" and "result__a" in cls:
            self.in_result = True
            self.in_link = True
            self.title = ""
            self.url = attrs.get("href", "")
        elif tag in ("a", "div") and "result__snippet" in cls:
            self.in_snippet = True
    def handle_endtag(self, tag):
        if tag == "a" and self.in_link:
            self.in_link = False
            if self.title.strip():
                self.results.append({"title": self.title.strip(), "url": self.url, "snippet": self.snippet.strip()})
                self.in_result = False
                self.snippet = ""
        if tag == "div" and self.in_snippet:
            self.in_snippet = False
    def handle_data(self, data):
        if self.in_link:
            self.title += data
        elif self.in_snippet:
            self.snippet += data

def live_search(query: str, limit: int = 5):
    encoded = urllib.parse.urlencode({"q": query, "kl": "in-en"})
    url = "https://html.duckduckgo.com/html/?" + encoded
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 MIRA/4.0"})
    with urllib.request.urlopen(req, timeout=12) as response:
        html = response.read().decode("utf-8", errors="ignore")
    parser = SearchParser()
    parser.feed(html)
    return parser.results[:limit]

def is_live_query(text: str):
    low = text.lower()
    triggers = ["latest", "today", "aaj", "abhi", "current", "news", "recent", "price", "rate", "weather", "result", "update", "2026"]
    return any(t in low for t in triggers)

def build_messages(session_id: str, user_message: str, web_results=None):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if web_results:
        evidence = []
        for i, r in enumerate(web_results, 1):
            evidence.append(f"[{i}] {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet'][:900]}")
        messages.append({"role": "system", "content": "LIVE WEB SEARCH RESULTS. Use these to answer the current query and mention sources when useful:\n\n" + "\n\n".join(evidence)[:6000]})
    for item in list(sessions[session_id]):
        content = str(item.get("content", ""))[:700]
        if content:
            messages.append({"role": item.get("role", "user"), "content": content})
    messages.append({"role": "user", "content": user_message[:2000]})
    return messages

def explicit_memory(text: str):
    low = text.lower()
    for trigger in ["yaad rakho", "yaad rakhna", "remember this", "save this", "memory me save", "memory mein save"]:
        idx = low.find(trigger)
        if idx >= 0:
            value = text[idx + len(trigger):].strip(" :-,.")
            return value or None
    return None

def save_memory_from_message(session_id: str, text: str):
    value = explicit_memory(text)
    if value and len(value) <= 600:
        key = "explicit_" + str(abs(hash(value)) % 100000000)
        save_memory(session_id, key, value, "explicit")
        return {"saved": True, "type": "explicit", "key": key}
    return {"saved": False}

@app.get("/")
def home():
    return {"assistant":"MIRA","status":"ONLINE","version":"4.0","model":MODEL,"memory":MEMORY_STATUS,"web_search":"server-side DuckDuckGo","message":"Boss, MIRA online hai."}

@app.get("/health")
def health():
    return {"status":"ok","assistant":"MIRA","model":MODEL,"memory":MEMORY_STATUS,"version":"4.0","groq_configured":bool(api_key)}

@app.get("/ask")
def ask(message: str = Query(..., min_length=1, max_length=12000), session_id: str = Query("boss", min_length=1, max_length=100)):
    if not api_key:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY is not configured")
    try:
        memory_result = save_memory_from_message(session_id, message)
        web_results = []
        web_used = False
        if is_live_query(message):
            try:
                web_results = live_search(message, 5)
                web_used = bool(web_results)
            except Exception as search_error:
                print(f"MIRA web search failed: {type(search_error).__name__}: {search_error}", flush=True)
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(model=MODEL, messages=build_messages(session_id, message, web_results), max_tokens=1200)
        assistant_message = response.choices[0].message
        answer = assistant_message.content or "Boss, mujhe is request ka clear answer nahi mila."
        sessions[session_id].append({"role":"user","content":message})
        sessions[session_id].append({"role":"assistant","content":answer})
        return {"assistant":"MIRA","response":answer,"model":MODEL,"memory":MEMORY_STATUS,"memory_action":memory_result,"live_web_used":web_used,"sources":[{"title":r["title"],"url":r["url"]} for r in web_results]}
    except Exception as exc:
        print(f"MIRA /ask failed: {type(exc).__name__}: {exc}", flush=True)
        raise HTTPException(status_code=502, detail=f"MIRA backend error: {type(exc).__name__}") from exc

@app.get("/memory")
def get_memory(session_id: str = Query("boss", min_length=1, max_length=100)):
    return {"assistant":"MIRA","session_id":session_id,"memories":list_memories(session_id,100)}

@app.post("/memory/save")
def memory_save(key: str = Query(..., min_length=1, max_length=100), value: str = Query(..., min_length=1, max_length=5000), category: str = Query("general", min_length=1, max_length=50), session_id: str = Query("boss", min_length=1, max_length=100)):
    try:
        save_memory(session_id,key.strip(),value.strip(),category.strip())
        return {"assistant":"MIRA","status":"saved","key":key.strip(),"category":category.strip()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Memory error: {type(exc).__name__}") from exc

@app.delete("/memory")
def memory_delete(key: str = Query(..., min_length=1, max_length=100), session_id: str = Query("boss", min_length=1, max_length=100)):
    try:
        delete_memory(session_id,key.strip())
        return {"assistant":"MIRA","status":"deleted","key":key.strip()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Memory error: {type(exc).__name__}") from exc

@app.post("/reset")
def reset(session_id: str = Query("boss", min_length=1, max_length=100)):
    sessions.pop(session_id,None)
    return {"assistant":"MIRA","status":"reset","session_id":session_id}
