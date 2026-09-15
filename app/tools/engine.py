"""Safe, inspectable tool engine for MIRA."""
from __future__ import annotations

import re
from app.tools.registry import ToolRegistry
from app.core.task_manager import TaskManager


class ActionEngine:
    def __init__(self):
        from app.tools.local import calculator, current_time, list_files, read_file, search_files, write_note
        self.registry = ToolRegistry()
        self.registry.register("calculator", calculator, "Calculate a basic arithmetic expression", "utility")
        self.registry.register("current_time", current_time, "Get the current local time", "utility")
        self.registry.register("list_files", list_files, "List files in the MIRA workspace", "files")
        self.registry.register("read_file", read_file, "Read a text or Markdown file", "files")
        self.registry.register("search_files", search_files, "Search workspace files", "files")
        self.registry.register("write_note", write_note, "Create a Markdown/text note", "files")
        self.tasks = TaskManager()

    def tools(self) -> list[str]: return self.registry.list_tools()
    def describe(self) -> list[dict]: return self.registry.describe()

    def route(self, message: str):
        text = message.strip(); low = text.lower()
        if low.startswith(("calculate ", "calc ", "hisab ", "hisaab ")):
            return "calculator", {"expression": re.sub(r"^(calculate|calc|hisab|hisaab)\s+", "", text, flags=re.I)}
        if any(p in low for p in ("what time is it", "current time", "abhi kitne baje", "abhi time kya hai")):
            return "current_time", {}
        if low in {"list files", "files dikhao", "workspace files dikhao", "meri files dikhao"}:
            return "list_files", {}
        m = re.match(r"^(?:search files|files search karo|file search karo)\s+(.+)$", text, re.I)
        if m: return "search_files", {"query": m.group(1).strip()}
        m = re.match(r"^(?:read|open|padho|padh)\s+(?:file\s+)?[\"']?([^\"']+?)[\"']?$", text, re.I)
        if m and m.group(1).strip().lower().endswith((".txt", ".md")):
            return "read_file", {"name": m.group(1).strip()}

        # Task/reminder commands. Dates/times are supplied as ISO strings by the UI/API,
        # keeping parsing deterministic and avoiding hidden assumptions about locale.
        m = re.match(r"^(?:add task|task add|kaam add karo|kaam save karo)\s+(.+)$", text, re.I)
        if m: return "add_task", {"title": m.group(1).strip()}
        m = re.match(r"^(?:remind me|reminder|yaad dilana|mujhe yaad dilana)\s+(.+)$", text, re.I)
        if m: return "reminder_request", {"text": m.group(1).strip()}
        if low in {"my tasks", "tasks dikhao", "pending tasks", "pending kaam", "mera pending kaam kya hai"}:
            return "list_tasks", {}
        if low in {"reminders dikhao", "my reminders", "pending reminders", "yaad dilane wali cheeze dikhao"}:
            return "list_reminders", {}
        if low in {"due tasks", "due kaam", "aaj ke tasks", "aaj ka kaam"}:
            return "due_tasks", {}
        if low.startswith(("complete task ", "complete ", "task complete ", "kaam complete ")):
            q = re.sub(r"^(complete task|complete|task complete|kaam complete)\s+", "", text, flags=re.I).strip()
            return "complete_task", {"query": q}
        if low in {"clear completed tasks", "completed tasks clear karo"}:
            return "clear_completed_tasks", {}
        return None

    def execute(self, name: str, **kwargs):
        if name == "add_task": return {"ok": True, "task": self.tasks.add(kwargs["title"])}
        if name == "list_tasks": return {"ok": True, "tasks": self.tasks.list("pending")}
        if name == "list_reminders":
            tasks = [t for t in self.tasks.list("pending") if t.get("reminder_at") or t.get("due_at")]
            return {"ok": True, "reminders": tasks}
        if name == "due_tasks": return {"ok": True, "tasks": self.tasks.due_or_reminders()}
        if name == "reminder_request":
            return {"ok": False, "needs_schedule": True, "text": kwargs["text"],
                    "message": "Reminder ka exact date/time chahiye. Example: 2026-09-16 09:00."}
        if name == "complete_task": return {"ok": True, "count": self.tasks.complete(kwargs["query"])}
        if name == "clear_completed_tasks": return {"ok": True, "count": self.tasks.clear_completed()}
        fn = self.registry.get(name)
        if fn is None: raise ValueError(f"tool not allowed: {name}")
        return fn(**kwargs)
