from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.core.assistant import MIRA

router = APIRouter()
mira = MIRA()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    session_id: str = Field(default="boss", min_length=1, max_length=100)


class RememberRequest(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=5000)
    category: str = Field(default="general", min_length=1, max_length=50)


@router.get("/api/health")
async def health():
    return {"status": "ok", "assistant": "MIRA", "version": "6.0.0", "memory": "ready"}


@router.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        reply = await mira.chat(req.message.strip(), req.session_id.strip())
        return {"assistant": "MIRA", "reply": reply, "session_id": req.session_id.strip()}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"MIRA backend error: {type(exc).__name__}") from exc


@router.get("/api/memory")
async def get_memory():
    return {"assistant": "MIRA", "memories": mira.memories()}


@router.post("/api/memory")
async def save_memory(req: RememberRequest):
    mira.remember(req.key, req.value, req.category)
    return {"assistant": "MIRA", "status": "saved", "key": req.key, "category": req.category}


@router.delete("/api/memory/{key}")
async def delete_memory(key: str):
    mira.forget(key)
    return {"assistant": "MIRA", "status": "deleted", "key": key}
