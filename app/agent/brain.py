"""Small, safe agent planner for MIRA.

The planner can choose an existing allowlisted tool or request web search.
It never creates executable code, shell commands, URLs to open, or new tools.
"""
from __future__ import annotations

import json
import re

from app.tools.engine import ActionEngine


class AgentBrain:
    def __init__(self, llm, actions: ActionEngine):
        self.llm = llm
        self.actions = actions

    def _fallback(self, message: str):
        return self.actions.route(message)

    async def plan(self, message: str, history: list[dict], system: str):
        """Return a safe plan: {action, tool, args} or None."""
        explicit = self._fallback(message)
        if explicit:
            return {"action": "tool", "tool": explicit[0], "args": explicit[1]}

        tools = self.actions.describe()
        tool_lines = "\n".join(
            f"- {item['name']}: {item['description']} ({item['category']})" for item in tools
        )
        planner_system = (
            "You are MIRA's internal action planner. Return ONLY valid JSON.\n"
            "Allowed action values: none, web_search, tool.\n"
            "If the user needs current/fresh internet information, choose web_search.\n"
            "Choose tool only when one listed tool directly matches the request.\n"
            "Never invent a tool. Never output shell commands, code, credentials, or URLs to open.\n"
            "For tool args, use only the arguments the tool obviously needs.\n"
            "JSON shape: {\"action\":\"none|web_search|tool\",\"tool\":\"name or null\",\"args\":{},\"query\":\"search query or null\"}"
            f"\n\nAVAILABLE TOOLS:\n{tool_lines}"
        )
        try:
            raw = await self.llm.generate(planner_system, history[-6:], message, web_search=False)
            match = re.search(r"\{.*\}", raw, re.S)
            if not match:
                return None
            data = json.loads(match.group(0))
            action = data.get("action")
            if action == "web_search":
                query = str(data.get("query") or message).strip()
                return {"action": "web_search", "query": query[:1000]}
            if action == "tool":
                tool = str(data.get("tool") or "")
                allowed = {x["name"] for x in tools}
                if tool not in allowed:
                    return None
                args = data.get("args") if isinstance(data.get("args"), dict) else {}
                return {"action": "tool", "tool": tool, "args": args}
        except Exception:
            return None
        return None
