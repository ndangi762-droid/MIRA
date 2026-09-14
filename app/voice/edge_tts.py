from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import edge_tts


class EdgeTTS:
    """Free online Microsoft Edge neural TTS adapter. No API key required."""

    def __init__(self):
        # Ananya is a clean, natural Hindi female neural voice for MIRA.
        self.voice = os.getenv("EDGE_TTS_VOICE", "hi-IN-AnanyaNeural")
        self.rate = os.getenv("EDGE_TTS_RATE", "-4%")
        self.pitch = os.getenv("EDGE_TTS_PITCH", "-1Hz")
        self.volume = os.getenv("EDGE_TTS_VOLUME", "+0%")

    @property
    def configured(self) -> bool:
        return True

    async def synthesize(self, text: str) -> bytes:
        text = text.strip()
        if not text:
            raise ValueError("TTS text cannot be empty")

        with tempfile.TemporaryDirectory(prefix="mira_edge_tts_") as tmp:
            output = Path(tmp) / "speech.mp3"
            communicate = edge_tts.Communicate(
                text,
                self.voice,
                rate=self.rate,
                volume=self.volume,
                pitch=self.pitch,
            )
            await communicate.save(str(output))
            if not output.exists() or output.stat().st_size == 0:
                raise RuntimeError("Edge TTS returned no audio")
            return output.read_bytes()
