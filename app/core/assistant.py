from app.core.prompts import SYSTEM_PROMPT
from app.llm.ollama import OllamaClient
from app.memory.store import MemoryStore


class MIRA:
    def __init__(self):
        self.llm = OllamaClient()
        self.memory = MemoryStore()

    def _memory_context(self):
        items = self.memory.memories(limit=20)
        if not items:
            return ""
        lines = [f"- {item['category']}: {item['value']}" for item in items]
        return "LONG-TERM MEMORY:\n" + "\n".join(lines)

    async def chat(self, message: str, session_id: str = "boss") -> str:
        history = self.memory.recent(limit=10, session_id=session_id)
        context = self._memory_context()
        system = SYSTEM_PROMPT
        if context:
            system += "\n\n" + context
        response = await self.llm.generate(system, history, message)
        self.memory.add("user", message, session_id)
        self.memory.add("assistant", response, session_id)
        return response

    def remember(self, key: str, value: str, category: str = "general"):
        self.memory.remember(key, value, category)

    def memories(self):
        return self.memory.memories()

    def forget(self, key: str):
        self.memory.forget(key)
