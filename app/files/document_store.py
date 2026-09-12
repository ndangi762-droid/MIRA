"""Local document ingestion for MIRA.

Supports plain text/Markdown and PDF extraction. Files stay inside the configured
MIRA workspace; uploads are size-limited and filenames are sanitized.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.tools.local import WORKSPACE, _safe_path

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def sanitize_name(name: str) -> str:
    name = Path(name or "document").name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return name[:160] or "document.txt"


def save_upload(filename: str, data: bytes) -> dict:
    safe_name = sanitize_name(filename)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("unsupported file type; use TXT, MD, or PDF")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("file is larger than 10 MB")
    target = _safe_path(safe_name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {"ok": True, "file": str(target.relative_to(WORKSPACE)), "bytes": len(data)}


def extract_text(name: str) -> dict:
    path = _safe_path(name.strip())
    if not path.is_file():
        raise FileNotFoundError(name)
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8", errors="replace")
    elif suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        chunks = [(page.extract_text() or "") for page in reader.pages]
        text = "\n\n".join(chunks)
    else:
        raise ValueError("unsupported file type")
    return {"ok": True, "file": str(path.relative_to(WORKSPACE)), "text": text[:100_000], "characters": len(text)}
