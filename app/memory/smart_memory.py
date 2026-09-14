import re


class SmartMemory:
    """Conservative memory gate: save durable facts, preferences and plans, not casual chat."""

    EXPLICIT_TRIGGERS = (
        "yaad rakho", "yaad rakhna", "remember this", "remember that",
        "save this", "memory me save", "memory mein save",
    )

    # These are intentionally narrower than the old rules. A word like "app" or
    # "main" by itself is not enough to create long-term memory.
    PATTERNS = {
        "profile": (
            r"\bmera naam\s+(?:hai|he)?\s*.+",
            r"\bmy name\s+is\s+.+",
            r"\bmeri age\s+(?:hai|he)?\s*\d+",
            r"\bmy age\s+is\s+\d+",
            r"\bmera birthday\b.*",
            r"\bi am\s+.+",
        ),
        "preference": (
            r"\bmujhe\s+.+\s+(?:pasand|acha|accha)\b.*",
            r"\bmujhe nahi pasand\b.*",
            r"\bi (?:prefer|like|hate)\s+.+",
        ),
        "project": (
            r"\b(?:mera|meri|mere)\s+(?:project|app|website)\b.*",
            r"\b(?:project|app|website)\s+(?:ka|ki|name|naam)\b.*",
            r"\bmera\s+(?:mira|printup|nrj graphics)\b.*",
        ),
        "plan": (
            r"\bmujhe\s+.+\s+seekhna\s+hai\b.*",
            r"\b(?:mujhe|main)\s+.+\s+(?:banana|karna)\s+hai\b.*",
            r"\b(?:mera|meri)\s+(?:goal|target|plan)\b.*",
            r"\bi (?:plan|want|intend)\s+to\s+.+",
        ),
    }

    def classify(self, message: str) -> str | None:
        text = message.strip().lower()
        if not text:
            return None
        if any(trigger in text for trigger in self.EXPLICIT_TRIGGERS):
            return "explicit"
        # Questions and short conversational lines should not become memories.
        if text.endswith("?") or len(text) < 12:
            return None
        for category, patterns in self.PATTERNS.items():
            if any(re.search(pattern, text) for pattern in patterns):
                return category
        return None

    def should_store(self, message: str) -> bool:
        return self.classify(message) is not None

    def make_key(self, message: str, category: str) -> str:
        text = re.sub(r"\s+", " ", message.lower()).strip()
        # Stable-ish keys keep repeated statements from creating lots of memories.
        if category == "profile":
            for marker in ("mera naam", "my name", "meri age", "my age", "mera birthday"):
                if marker in text:
                    value = text[text.find(marker):]
                    return f"profile_{re.sub(r'[^a-z0-9]+', '_', value)[:60].strip('_')}"
        clean = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")[:70]
        return f"smart_{category}_{clean or 'memory'}"
