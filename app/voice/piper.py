from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path


class PiperTTS:
    """Free local Piper TTS adapter. No API key or cloud service required."""

    def __init__(self):
        self.voice = os.getenv("PIPER_VOICE", "hi_IN-priyamvada-medium")
        self.model_path = Path(os.getenv("PIPER_MODEL_PATH", "models/piper/hi_IN-priyamvada-medium.onnx"))
        self.binary = os.getenv("PIPER_BINARY", "piper")

    @property
    def configured(self) -> bool:
        return bool(self._binary_path() and self.model_path.exists())

    def _binary_path(self) -> str | None:
        return shutil.which(self.binary)

    async def synthesize(self, text: str) -> bytes:
        if not self.configured:
            raise RuntimeError("Piper is not installed/configured. Run scripts\\setup_piper.ps1 first.")

        with tempfile.TemporaryDirectory(prefix="mira_piper_") as tmp:
            wav_path = Path(tmp) / "speech.wav"
            cmd = [
                self._binary_path() or self.binary,
                "--model", str(self.model_path),
                "--output_file", str(wav_path),
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate(text.encode("utf-8"))
            if proc.returncode != 0 or not wav_path.exists():
                detail = stderr.decode("utf-8", errors="ignore").strip()
                raise RuntimeError(f"Piper TTS failed: {detail[:500]}")
            return wav_path.read_bytes()
