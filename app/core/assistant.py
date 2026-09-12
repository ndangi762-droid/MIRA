import re

from app.core.prompts import SYSTEM_PROMPT
from app.llm.client import LLMClient
from app.memory.store import MemoryStore
from app.tools.engine import ActionEngine


class MIRA:
    def __init__(self):
        self.llm = LLMClient()
        self.memory = MemoryStore()
        self.actions = ActionEngine()

    def _memory_context(self):
        items = self.memory.memories(limit=20)
        if not items:
            return ""
        lines = [f"- {item['category']}: {item['value']}" for item in items]
        return "LONG-TERM MEMORY:\n" + "\n".join(lines)

    def _capture_memory_request(self, message: str):
        text = message.strip()
        low = text.lower()
        triggers = (
            "yaad rakho", "yaad rakhna", "remember this", "remember that",
            "save this", "memory me save", "memory mein save",
        )
        trigger = next((t for t in triggers if t in low), None)
        if not trigger:
            return None
        value = text[low.find(trigger) + len(trigger):].strip(" :-,.\n\t")
        if not value or len(value) > 1000:
            return None
        key_base = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")[:70]
        self.memory.remember("explicit_" + (key_base or "memory"), value, "explicit")
        return value

    def _action_reply(self, tool_name: str, result: dict) -> str:
        if tool_name == "calculator":
            return f"Boss, result: {result['result']}"
        if tool_name == "current_time":
            return f"Boss, abhi local time: {result['iso']}"
        if tool_name == "list_files":
            files = result.get("files", [])
            return "Boss, MIRA workspace abhi empty hai." if not files else "Boss, workspace mein ye files hain:\n" + "\n".join(f"• {x}" for x in files[:50])
        if tool_name == "search_files":
            matches = result.get("matches", [])
            return f"Boss, '{result['query']}' ka koi match nahi mila." if not matches else "Boss, matches mile:\n" + "\n".join(f"• {x}" for x in matches[:50])
        return "Boss, action complete ho gaya."

    async def chat(self, message: str, session_id: str = "boss") -> str:
        saved = self._capture_memory_request(message)
        history = self.memory.recent(limit=10, session_id=session_id)
        if saved:
            response = await self.llm.generate(
                SYSTEM_PROMPT + "\n\nIMPORTANT: Boss explicitly asked to save a memory. Confirm briefly and naturally that it has been saved.",
                history, message,
            )
        else:
            action = self.actions.route(message)
            if action:
                tool_name, kwargs = action
                try:
                    result = self.actions.execute(tool_name, **kwargs)
                    response = self._action_reply(tool_name, result)
                except Exception as exc:
                    response = f"Boss, action run nahi ho saka: {type(exc).__name__}."
            else:
                context = self._memory_context()
                system = SYSTEM_PROMPT + ("\n\n" + context if context else "")
                web_search = message.lower().startswith(("search web ", "web search ", "internet par search ", "latest search "))
                if web_search:
                    clean = re.sub(r"^(search web|web search|internet par search|latest search)\s+", "", message, flags=re.I)
                    response = await self.llm.generate(system, history, clean, web_search=True)
                else:
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
