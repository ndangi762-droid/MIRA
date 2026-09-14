import re
from typing import AsyncIterator

from app.core.prompts import SYSTEM_PROMPT
from app.core.style_engine import StyleEngine
from app.llm.client import LLMClient
from app.memory.smart_memory import SmartMemory
from app.memory.store import MemoryStore
from app.tools.engine import ActionEngine


class MIRA:
    def __init__(self):
        self.llm = LLMClient()
        self.memory = MemoryStore()
        self.actions = ActionEngine()
        self.style = StyleEngine()
        self.smart_memory = SmartMemory()

    def _memory_context(self):
        items = self.memory.memories(limit=20)
        if not items:
            return ""
        lines = [f"- {item['category']}: {item['value']}" for item in items]
        return "LONG-TERM MEMORY:\n" + "\n".join(lines)

    def _capture_memory_request(self, message: str):
        text = message.strip()
        low = text.lower()
        triggers = ("yaad rakho", "yaad rakhna", "remember this", "remember that", "save this", "memory me save", "memory mein save")
        trigger = next((t for t in triggers if t in low), None)
        if not trigger:
            return None
        value = text[low.find(trigger) + len(trigger):].strip(" :-,.\n\t")
        if not value or len(value) > 1000:
            return None
        key_base = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")[:70]
        self.memory.remember("explicit_" + (key_base or "memory"), value, "explicit")
        return value

    def _capture_smart_memory(self, message: str):
        if not self.smart_memory.should_store(message):
            return None
        category = self.smart_memory.classify(message)
        if category == "explicit" or not category:
            return None
        key = self.smart_memory.make_key(message, category)
        self.memory.remember(key, message.strip(), category)
        return category

    def _memory_command(self, message: str):
        """Handle explicit memory inspection/removal without sending sensitive commands to the LLM."""
        low = message.strip().lower()
        show_triggers = ("meri memory dikhao", "memory dikhao", "show my memories", "show memory", "what do you remember about me", "tumhe mere baare mein kya yaad hai")
        if low in show_triggers:
            items = self.memory.memories(limit=50)
            if not items:
                return "Boss, abhi long-term memory mein kuch saved nahi hai."
            lines = [f"• [{item['category']}] {item['value']}" for item in items]
            return "Boss, mujhe ye important baatein yaad hain:\n" + "\n".join(lines)

        for prefix in ("memory search ", "search memory "):
            if low.startswith(prefix):
                query = message.strip()[len(prefix):].strip()
                if not query:
                    return "Boss, memory mein kis cheez ko search karna hai?"
                items = self.memory.find_memories(query)
                if not items:
                    return f"Boss, '{query}' se related memory nahi mili."
                return "Boss, ye memories mili:\n" + "\n".join(f"• [{x['category']}] {x['value']}" for x in items)

        for prefix in ("memory bhool jao ", "memory bhul jao ", "forget memory ", "forget "):
            if low.startswith(prefix):
                query = message.strip()[len(prefix):].strip()
                if not query:
                    return "Boss, kis memory ko bhoolna hai?"
                count = self.memory.forget_matching(query)
                return f"Boss, {count} matching memory {'delete ho gayi' if count == 1 else 'delete ho gayi hain'}."
        return None

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
        if tool_name == "read_file":
            return f"Boss, {result['file']} ka content:\n\n{result['content']}"
        return "Boss, action complete ho gaya."

    def _build_prompt(self, message: str, history: list[dict]):
        style_context = self.style.examples_for(message, limit=3)
        style_block = ("\n\n" + style_context + "\nUse these examples as STYLE guidance only. Do not copy them unless they directly fit the conversation." if style_context else "")
        smart_category = self.smart_memory.classify(message) if self.smart_memory.should_store(message) else None
        memory_notice = f"\n\nThis message was classified as useful long-term memory in category: {smart_category}." if smart_category else ""
        context = self._memory_context()
        system = SYSTEM_PROMPT + style_block + memory_notice + ("\n\n" + context if context else "")
        return system, history

    async def chat(self, message: str, session_id: str = "boss") -> str:
        parts = []
        async for delta in self.stream(message, session_id):
            parts.append(delta)
        return "".join(parts)

    async def stream(self, message: str, session_id: str = "boss") -> AsyncIterator[str]:
        memory_command = self._memory_command(message)
        if memory_command is not None:
            yield memory_command
            self.memory.add("user", message, session_id)
            self.memory.add("assistant", memory_command, session_id)
            return

        saved = self._capture_memory_request(message)
        smart_category = None if saved else self._capture_smart_memory(message)
        history = self.memory.recent(limit=10, session_id=session_id)

        if saved:
            style_context = self.style.examples_for(message, limit=3)
            style_block = ("\n\n" + style_context + "\nUse these examples as STYLE guidance only. Do not copy them unless they directly fit the conversation." if style_context else "")
            system = SYSTEM_PROMPT + style_block + "\n\nIMPORTANT: Boss explicitly asked to save a memory. Confirm briefly and naturally that it has been saved."
            parts = []
            async for delta in self.llm.stream(system, history, message):
                parts.append(delta)
                yield delta
            response = "".join(parts)
        else:
            action = self.actions.route(message)
            if action:
                tool_name, kwargs = action
                try:
                    result = self.actions.execute(tool_name, **kwargs)
                    response = self._action_reply(tool_name, result)
                except Exception as exc:
                    response = f"Boss, action run nahi ho saka: {type(exc).__name__}."
                yield response
            else:
                system, history = self._build_prompt(message, history)
                web_search = message.lower().startswith(("search web ", "web search ", "internet par search ", "latest search "))
                if web_search:
                    clean = re.sub(r"^(search web|web search|internet par search|latest search)\s+", "", message, flags=re.I)
                    parts = []
                    async for delta in self.llm.stream(system, history, clean, web_search=True):
                        parts.append(delta)
                        yield delta
                    response = "".join(parts)
                else:
                    parts = []
                    async for delta in self.llm.stream(system, history, message):
                        parts.append(delta)
                        yield delta
                    response = "".join(parts)

        self.memory.add("user", message, session_id)
        self.memory.add("assistant", response, session_id)

    def remember(self, key: str, value: str, category: str = "general"):
        self.memory.remember(key, value, category)

    def memories(self):
        return self.memory.memories()

    def forget(self, key: str):
        self.memory.forget(key)
