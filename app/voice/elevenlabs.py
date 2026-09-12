from __future__ import annotations

import httpx

from app.config import (
    ELEVENLABS_API_KEY,
    ELEVENLABS_MODEL,
    ELEVENLABS_VOICE_ID,
)


class ElevenLabsTTS:
    """Server-side ElevenLabs TTS adapter. The API key never reaches the browser."""

    def __init__(self):
        self.base_url = "https://api.elevenlabs.io/v1"

    @property
    def configured(self) -> bool:
        return bool(ELEVENLABS_API_KEY.strip() and ELEVENLABS_VOICE_ID.strip())

    async def synthesize(self, text: str) -> bytes:
        if not self.configured:
            raise RuntimeError("ElevenLabs voice is not configured")

        url = f"{self.base_url}/text-to-speech/{ELEVENLABS_VOICE_ID}"
        payload = {
            "text": text,
            "model_id": ELEVENLABS_MODEL,
            "voice_settings": {
                "stability": 0.42,
                "similarity_boost": 0.78,
                "style": 0.32,
                "use_speaker_boost": True,
            },
        }
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }

        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.content
