from __future__ import annotations

import asyncio
import os
import re
import tempfile
from pathlib import Path

import edge_tts


# Common Roman-Hindi words are rendered in Devanagari only for speech.
# The chat UI remains unchanged in Roman Hinglish.
_HINDI_SPEECH = {
    "haan": "हाँ", "han": "हाँ", "nahi": "नहीं", "nahin": "नहीं",
    "acha": "अच्छा", "accha": "अच्छा", "achha": "अच्छा",
    "theek": "ठीक", "thik": "ठीक", "hai": "है", "he": "है",
    "ho": "हो", "hoga": "होगा", "hogi": "होगी", "hain": "हैं",
    "kya": "क्या", "kyu": "क्यों", "kyon": "क्यों", "kaise": "कैसे",
    "kaisa": "कैसा", "kaisi": "कैसी", "kab": "कब", "kahan": "कहाँ",
    "kahaan": "कहाँ", "kaun": "कौन", "mera": "मेरा", "meri": "मेरी",
    "mere": "मेरे", "mujhe": "मुझे", "main": "मैं", "mein": "में",
    "tum": "तुम", "aap": "आप", "ap": "आप", "batao": "बताओ",
    "bolo": "बोलो", "sun": "सुन", "suno": "सुनो", "dekho": "देखो",
    "dekh": "देख", "kar": "कर", "karo": "करो", "kr": "कर",
    "kuch": "कुछ", "koi": "कोई", "sab": "सब", "ab": "अब",
    "aur": "और", "ya": "या", "lekin": "लेकिन", "bas": "बस",
    "bahut": "बहुत", "bohot": "बहुत", "bilkul": "बिल्कुल",
    "ek": "एक", "do": "दो", "ye": "ये", "yah": "यह", "wo": "वो",
    "woh": "वो", "iska": "इसका", "uska": "उसका", "kyunki": "क्योंकि",
    "phir": "फिर", "abhi": "अभी", "yahan": "यहाँ", "wahan": "वहाँ",
    "chal": "चल", "chalo": "चलो", "karna": "करना", "karni": "करनी",
    "karta": "करता", "karte": "करते", "raha": "रहा", "rha": "रहा",
    "rahi": "रही", "rhi": "रही", "sakta": "सकता", "sakti": "सकती",
    "chahiye": "चाहिए", "chahta": "चाहता", "chahti": "चाहती",
    "acchi": "अच्छी", "achhi": "अच्छी", "mast": "मस्त", "maza": "मज़ा",
    "majja": "मज़ा", "yaar": "यार", "boss": "बॉस",
}


def _speech_text(text: str) -> str:
    """Convert common Roman-Hindi words to Devanagari for better Hindi TTS."""
    def replace(match: re.Match[str]) -> str:
        word = match.group(0)
        return _HINDI_SPEECH.get(word.lower(), word)

    return re.sub(r"[A-Za-z]+", replace, text)


class EdgeTTS:
    """Free online Microsoft Edge neural TTS adapter. No API key required."""

    def __init__(self):
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

        speech_text = _speech_text(text)

        with tempfile.TemporaryDirectory(prefix="mira_edge_tts_") as tmp:
            output = Path(tmp) / "speech.mp3"
            communicate = edge_tts.Communicate(
                speech_text,
                self.voice,
                rate=self.rate,
                volume=self.volume,
                pitch=self.pitch,
            )
            await communicate.save(str(output))
            if not output.exists() or output.stat().st_size == 0:
                raise RuntimeError("Edge TTS returned no audio")
            return output.read_bytes()
