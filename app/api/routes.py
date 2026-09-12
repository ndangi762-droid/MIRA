from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from app.core.assistant import MIRA
from app.files.document_store import save_upload, extract_text

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
    return {"status": "ok", "assistant": "MIRA", "version": "7.1.0", "memory": "ready", "documents": "ready"}


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


@router.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        data = await file.read()
        return save_upload(file.filename or "document.txt", data)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/files/read")
async def read_document(name: str):
    try:
        return extract_text(name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"file not found: {name}") from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
