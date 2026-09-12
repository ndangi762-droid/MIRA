from __future__ import annotations

import asyncio
import os
import shutil
import sys
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
        return self.model_path.exists() and self._command() is not None

    def _command(self) -> list[str] | None:
        # Prefer the Piper executable installed alongside MIRA's Python venv.
        venv_piper = Path(sys.executable).with_name("piper.exe")
        if venv_piper.exists():
            return [str(venv_piper)]
        found = shutil.which(self.binary)
        if found:
            return [found]
        # Piper TTS also exposes a Python module entry point.
        return [sys.executable, "-m", "piper"]

    async def synthesize(self, text: str) -> bytes:
        if not self.model_path.exists():
            raise RuntimeError("Piper Hindi voice model is missing. Run scripts\\setup_piper.ps1 first.")

        command = self._command()
        if command is None:
            raise RuntimeError("Piper TTS is not installed in the MIRA environment.")

        with tempfile.TemporaryDirectory(prefix="mira_piper_") as tmp:
            wav_path = Path(tmp) / "speech.wav"
            cmd = command + [
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
