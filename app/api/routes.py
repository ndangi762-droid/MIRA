from fastapi import APIRouter
from pydantic import BaseModel
from app.core.assistant import MIRA

router = APIRouter()
mira = MIRA()

class ChatRequest(BaseModel):
    message: str

@router.get("/api/health")
async def health():
    return {"status": "ok", "assistant": "MIRA"}

@router.post("/api/chat")
async def chat(req: ChatRequest):
    if not req.message.strip():
        return {"reply": "Boss, message empty hai."}
    return {"reply": await mira.chat(req.message.strip())}
