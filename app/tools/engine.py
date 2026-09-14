"""Safe, inspectable tool engine for MIRA.

Only registered allowlisted tools can execute. Natural-language routing remains
conservative; no arbitrary shell or code execution is exposed.
"""
from __future__ import annotations

import re
from app.tools.registry import ToolRegistry


class ActionEngine:
    def __init__(self):
        from app.tools.local import calculator, current_time, list_files, read_file, search_files, write_note

        self.registry = ToolRegistry()
        self.registry.register("calculator", calculator, "Calculate a basic arithmetic expression", "utility")
        self.registry.register("current_time", current_time, "Get the current local time", "utility")
        self.registry.register("list_files", list_files, "List files in the MIRA workspace", "files")
        self.registry.register("read_file", read_file, "Read a text or Markdown file from the MIRA workspace", "files")
        self.registry.register("search_files", search_files, "Search text and filenames in the MIRA workspace", "files")
        self.registry.register("write_note", write_note, "Create or replace a Markdown/text note in the MIRA workspace", "files")

    def tools(self) -> list[str]:
        return self.registry.list_tools()

    def describe(self) -> list[dict]:
        return self.registry.describe()

    def route(self, message: str):
        """Return (tool_name, kwargs) only for explicit, safe commands."""
        text = message.strip()
        low = text.lower()

        if low.startswith(("calculate ", "calc ", "hisab ", "hisaab ")):
            expression = re.sub(r"^(calculate|calc|hisab|hisaab)\s+", "", text, flags=re.I)
            return "calculator", {"expression": expression}

        if any(p in low for p in ("what time is it", "current time", "abhi kitne baje", "abhi time kya hai")):
            return "current_time", {}

        if low in {"list files", "files dikhao", "workspace files dikhao", "meri files dikhao"}:
            return "list_files", {}

        m = re.match(r"^(?:search files|files search karo|file search karo)\s+(.+)$", text, re.I)
        if m:
            return "search_files", {"query": m.group(1).strip()}

        m = re.match(r"^(?:read|open|padho|padh)\s+(?:file\s+)?[\"']?([^\"']+?)[\"']?$", text, re.I)
        if m and m.group(1).strip().lower().endswith((".txt", ".md")):
            return "read_file", {"name": m.group(1).strip()}

        return None

    def execute(self, name: str, **kwargs):
        fn = self.registry.get(name)
        if fn is None:
            raise ValueError(f"tool not allowed: {name}")
        return fn(**kwargs)
