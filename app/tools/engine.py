"""Safe action engine for MIRA.

The engine intentionally exposes a small allowlist of local tools. Natural-language
routing is conservative: only explicit, unambiguous requests are executed.
"""
from __future__ import annotations

import re
from app.tools.registry import ToolRegistry


class ActionEngine:
    def __init__(self):
        from app.tools.local import (
            calculator,
            current_time,
            list_files,
            read_file,
            search_files,
            write_note,
        )

        self.registry = ToolRegistry()
        self.registry.register("calculator", calculator)
        self.registry.register("current_time", current_time)
        self.registry.register("list_files", list_files)
        self.registry.register("read_file", read_file)
        self.registry.register("search_files", search_files)
        self.registry.register("write_note", write_note)

    def tools(self) -> list[str]:
        return self.registry.list_tools()

    def route(self, message: str):
        """Return (tool_name, kwargs) only for explicit safe commands."""
        text = message.strip()
        low = text.lower()

        # Calculator: explicit calculation phrasing only.
        if low.startswith(("calculate ", "calc ", "hisab ", "hisaab ")):
            expression = re.sub(r"^(calculate|calc|hisab|hisaab)\s+", "", text, flags=re.I)
            return "calculator", {"expression": expression}

        # Time: explicit current-time questions.
        if any(p in low for p in (
            "what time is it",
            "current time",
            "abhi kitne baje",
            "abhi time kya hai",
        )):
            return "current_time", {}

        # Workspace listing/search are deliberately explicit.
        if low in {"list files", "files dikhao", "workspace files dikhao", "meri files dikhao"}:
            return "list_files", {}

        m = re.match(r"^(?:search files|files search karo|file search karo)\s+(.+)$", text, re.I)
        if m:
            return "search_files", {"query": m.group(1).strip()}

        return None

    def execute(self, name: str, **kwargs):
        fn = self.registry.tools.get(name)
        if fn is None:
            raise ValueError(f"tool not allowed: {name}")
        return fn(**kwargs)
