from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    handler: Callable[..., Any]
    category: str = "general"


class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, Callable[..., Any]] = {}
        self.specs: dict[str, ToolSpec] = {}

    def register(self, name, fn, description: str = "", category: str = "general"):
        self.tools[name] = fn
        self.specs[name] = ToolSpec(name, description or name, fn, category)

    def list_tools(self):
        return list(self.tools.keys())

    def describe(self):
        return [
            {"name": s.name, "description": s.description, "category": s.category}
            for s in self.specs.values()
        ]

    def get(self, name):
        return self.tools.get(name)
