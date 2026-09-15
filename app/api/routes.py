import json
import logging

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from app.core.assistant import MIRA
from app.core.task_manager import TaskManager
from app.core.morning_brief import MorningBrief
from app.files.document_store import save_upload, extract_text
from app.voice.edge_tts import EdgeTTS
from app.config import GEMINI_API_KEY, GEMINI_MODEL
import httpx

logger = logging.getLogger(__name__)
router = APIRouter()
mira = MIRA()
tts = EdgeTTS()
tasks = TaskManager()
brief = MorningBrief(mira.llm)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    session_id: str = Field(default="boss", min_length=1, max_length=100)


class DocumentAskRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=200)
    question: str = Field(min_length=1, max_length=12000)
    session_id: str = Field(default="boss", min_length=1, max_length=100)


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class RememberRequest(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=5000)
    category: str = Field(default="general", min_length=1, max_length=50)


class SessionRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)


class TaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    priority: str = Field(default="normal", pattern="^(low|normal|high)$")
    due_at: str | None = Field(default=None, max_length=80)
    reminder_at: str | None = Field(default=None, max_length=80)


class CompleteTaskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)


@router.get("/api/health")
async def health():
    return {"status": "ok", "assistant": "MIRA", "version": "7.9.1", "memory": "ready", "documents": "qa-ready", "sessions": "ready", "streaming": "ready", "tasks": "ready", "reminders": "ready", "morning_brief": "ready", "voice": "edge-hindi-female", "mobile_transcription": "gemini-audio"}


@router.get("/api/brief/morning")
async def morning_brief():
    try:
        return {"assistant": "MIRA", "type": "morning_brief", "brief": await brief.generate()}
    except Exception as exc:
        logger.exception("MIRA morning brief failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail=f"Morning brief error: {type(exc).__name__}: {str(exc)[:300]}") from exc


@router.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        session_id = req.session_id.strip()
        mira.memory.ensure_session(session_id)
        reply = await mira.chat(req.message.strip(), session_id)
        return {"assistant": "MIRA", "reply": reply, "session_id": session_id}
    except Exception as exc:
        logger.exception("MIRA chat failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail=f"MIRA backend error: {type(exc).__name__}: {str(exc)[:300]}") from exc


@router.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    session_id = req.session_id.strip()
    message = req.message.strip()
    mira.memory.ensure_session(session_id)

    async def events():
        try:
            async for delta in mira.stream(message, session_id):
                yield json.dumps({"delta": delta}, ensure_ascii=False) + "\n"
            yield json.dumps({"done": True, "session_id": session_id}, ensure_ascii=False) + "\n"
        except Exception as exc:
            logger.exception("MIRA stream failed: %s", type(exc).__name__)
            yield json.dumps({"error": f"MIRA backend error: {type(exc).__name__}: {str(exc)[:300]}"}, ensure_ascii=False) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/api/voice/transcribe")
async def voice_transcribe(file: UploadFile = File(...)):
    """Transcribe a short microphone recording with the configured Gemini model."""
    if not GEMINI_API_KEY.strip():
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty audio recording")
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="audio recording is too large")

    mime = (file.content_type or "audio/mp4").split(";")[0].strip().lower()
    allowed = {"audio/mp4", "audio/webm", "audio/wav", "audio/wave", "audio/x-wav", "audio/mpeg", "audio/ogg", "audio/aac", "audio/m4a"}
    if mime not in allowed:
        mime = "audio/mp4"

    import base64
    payload = {
        "contents": [{"role": "user", "parts": [
            {"text": "Transcribe this audio exactly. Return only the spoken words, with no labels, explanation, punctuation commentary, or extra text. The speaker may use Hindi, Hinglish, or English. Preserve the speaker's wording."},
            {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode("ascii")}},
        ]}]
    }
    model = GEMINI_MODEL.strip() or "gemini-3.1-flash-lite"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    try:
        async with httpx.AsyncClient(timeout=90, trust_env=False) as client:
            response = await client.post(url, headers={"x-goog-api-key": GEMINI_API_KEY.strip(), "Content-Type": "application/json"}, json=payload)
            if response.is_error:
                detail = response.text.strip().replace("\n", " ")[:800]
                raise HTTPException(status_code=502, detail=f"Gemini transcription error: HTTP {response.status_code}: {detail}")
            result = response.json()
        text = "".join(part.get("text", "") for candidate in result.get("candidates", []) for part in candidate.get("content", {}).get("parts", []) if part.get("text")).strip()
        if not text:
            raise HTTPException(status_code=502, detail="Gemini returned no transcription")
        return {"assistant": "MIRA", "text": text, "mime_type": mime}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("MIRA voice transcription failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail=f"Voice transcription error: {type(exc).__name__}") from exc


@router.get("/api/tasks")
async def get_tasks(status: str = "pending"):
    if status not in {"pending", "completed"}:
        raise HTTPException(status_code=400, detail="status must be pending or completed")
    return {"assistant": "MIRA", "tasks": tasks.list(status)}


@router.post("/api/tasks")
async def add_task(req: TaskRequest):
    try:
        return {"assistant": "MIRA", "status": "created", "task": tasks.add(req.title, req.priority, req.due_at, req.reminder_at)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/tasks/due")
async def get_due_tasks():
    return {"assistant": "MIRA", "tasks": tasks.due_or_reminders()}


@router.post("/api/tasks/complete")
async def complete_task(req: CompleteTaskRequest):
    count = tasks.complete(req.query.strip())
    return {"assistant": "MIRA", "status": "completed", "count": count}


@router.delete("/api/tasks/completed")
async def clear_completed_tasks():
    count = tasks.clear_completed()
    return {"assistant": "MIRA", "status": "cleared", "count": count}


@router.post("/api/documents/ask")
async def ask_document(req: DocumentAskRequest):
    try:
        return {"assistant": "MIRA", "file": req.filename.strip(), "reply": await mira.ask_document(req.filename.strip(), req.question.strip(), req.session_id.strip())}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"file not found: {req.filename}")
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("MIRA document Q&A failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail=f"Document Q&A error: {type(exc).__name__}: {str(exc)[:300]}") from exc


@router.post("/api/voice/speak")
async def voice_speak(req: TTSRequest):
    try:
        audio = await tts.synthesize(req.text.strip())
        return Response(content=audio, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Edge TTS error: {type(exc).__name__}") from exc


@router.get("/api/voice/status")
async def voice_status():
    return {"provider": "edge-tts", "configured": tts.configured, "voice": tts.voice, "rate": tts.rate, "pitch": tts.pitch}


@router.get("/api/sessions")
async def get_sessions():
    return {"assistant": "MIRA", "sessions": mira.memory.sessions()}


@router.post("/api/sessions")
async def create_session(req: SessionRequest):
    mira.memory.ensure_session(req.session_id.strip(), req.title.strip())
    return {"assistant": "MIRA", "status": "created", "session_id": req.session_id.strip(), "title": req.title.strip()}


@router.patch("/api/sessions/{session_id}")
async def rename_session(session_id: str, req: SessionRequest):
    if req.session_id.strip() != session_id:
        raise HTTPException(status_code=400, detail="session_id mismatch")
    mira.memory.rename_session(session_id, req.title)
    return {"assistant": "MIRA", "status": "renamed", "session_id": session_id, "title": req.title.strip()}


@router.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    if session_id == "boss":
        raise HTTPException(status_code=400, detail="main session cannot be deleted")
    mira.memory.delete_session(session_id)
    return {"assistant": "MIRA", "status": "deleted", "session_id": session_id}


@router.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, limit: int = 100):
    limit = max(1, min(limit, 500))
    return {"assistant": "MIRA", "session_id": session_id, "messages": mira.memory.recent(limit, session_id)}


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
