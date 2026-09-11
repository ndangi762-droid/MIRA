from app.core.prompts import SYSTEM_PROMPT
from app.llm.ollama import OllamaClient
from app.memory.store import MemoryStore

class MIRA:
    def __init__(self):
        self.llm = OllamaClient()
        self.memory = MemoryStore()

    async def chat(self, message: str) -> str:
        history = self.memory.recent(limit=8)
        response = await self.llm.generate(SYSTEM_PROMPT, history, message)
        self.memory.add("user", message)
        self.memory.add("assistant", response)
        return response
