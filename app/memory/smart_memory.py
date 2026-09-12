import re


class SmartMemory:
    """Decides which user messages are worth promoting into long-term memory."""

    CATEGORY_RULES = {
        "profile": ("mera naam", "my name", "main", "i am", "meri age", "my age", "mera birthday"),
        "preference": ("mujhe pasand", "mujhe acha", "mujhe accha", "i prefer", "i like", "i hate", "mujhe nahi pasand"),
        "project": ("project", "app", "website", "mira", "nrj graphics", "printup", "coding"),
        "plan": ("plan", "planning", "goal", "target", "karunga", "karungi", "banana hai", "seekhna hai"),
    }

    EXPLICIT_TRIGGERS = (
        "yaad rakho", "yaad rakhna", "remember this", "remember that",
        "save this", "memory me save", "memory mein save",
    )

    def classify(self, message: str) -> str | None:
        text = message.strip().lower()
        if not text:
            return None
        if any(trigger in text for trigger in self.EXPLICIT_TRIGGERS):
            return "explicit"
        for category, patterns in self.CATEGORY_RULES.items():
            if any(pattern in text for pattern in patterns):
                return category
        return None

    def should_store(self, message: str) -> bool:
        text = message.strip().lower()
        if len(text) < 8:
            return False
        if text.endswith("?") and not any(x in text for x in ("mera", "meri", "mujhe", "main", "my ", "i ")):
            return False
        return self.classify(text) is not None

    def make_key(self, message: str, category: str) -> str:
        clean = re.sub(r"[^a-zA-Z0-9]+", "_", message.lower()).strip("_")[:70]
        return f"smart_{category}_{clean or 'memory'}"
