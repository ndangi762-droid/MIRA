import re


class SmartMemory:
    """Conservative memory gate for durable facts, preferences and plans."""

    EXPLICIT_TRIGGERS = (
        "yaad rakho", "yaad rakhna", "remember this", "remember that",
        "save this", "memory me save", "memory mein save",
    )

    # Only save statements that look durable. Casual mentions and questions stay out.
    PATTERNS = {
        "profile": (
            r"\bmera naam\s+(?:hai|he)?\s*[a-z][a-z .'-]{1,60}$",
            r"\bmy name\s+is\s+[a-z][a-z .'-]{1,60}$",
            r"\bmeri age\s+(?:hai|he)?\s*\d{1,3}\b",
            r"\bmy age\s+is\s+\d{1,3}\b",
            r"\bmera birthday\b.*",
            r"\bmera preferred name\b.*",
            r"\bmy preferred name\b.*",
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
        text = re.sub(r"\s+", " ", message.strip().lower())
        if not text:
            return None
        if any(trigger in text for trigger in self.EXPLICIT_TRIGGERS):
            return "explicit"
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

        # Profile facts get stable keys, so an update replaces the old value
        # instead of leaving stale memories beside the new one.
        if category == "profile":
            if re.search(r"\b(?:mera naam|my name)\b", text):
                return "profile_name"
            if re.search(r"\b(?:meri age|my age)\b", text):
                return "profile_age"
            if "birthday" in text:
                return "profile_birthday"
            if "preferred name" in text:
                return "profile_preferred_name"

        # Keep durable preferences/projects/plans deduplicated by normalized text.
        clean = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")[:70]
        return f"smart_{category}_{clean or 'memory'}"
