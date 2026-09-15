from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class PlanStep:
    number: int
    title: str
    status: str = "pending"


@dataclass
class Plan:
    goal: str
    steps: List[PlanStep] = field(default_factory=list)


class Planner:
    """Lightweight, safe planner for breaking a Boss's goal into actionable steps."""

    _verbs = (
        "build", "create", "make", "setup", "set up", "learn", "plan", "develop",
        "design", "research", "prepare", "start", "launch", "fix", "improve",
        "banao", "banana", "karo", "seekho", "sikho", "setup karo", "develop karo",
        "design karo", "research karo", "plan karo", "fix karo", "improve karo",
    )

    def should_plan(self, message: str) -> bool:
        text = message.strip().lower()
        if len(text) < 18:
            return False
        return any(v in text for v in self._verbs) and any(
            x in text for x in ("step", "kaise", "how", "roadmap", "plan", "project", "system", "app", "website", "assistant", "mira")
        )

    def create(self, goal: str) -> Plan:
        clean = re.sub(r"\s+", " ", goal.strip()).strip(" .")
        steps = [
            PlanStep(1, "Goal ko clearly define karna"),
            PlanStep(2, "Requirements aur available resources identify karna"),
            PlanStep(3, "Implementation ko small tasks mein todna"),
            PlanStep(4, "Ek-ek task safely execute aur test karna"),
            PlanStep(5, "Result verify karke next improvement decide karna"),
        ]
        return Plan(clean, steps)

    def format(self, plan: Plan) -> str:
        lines = [f"Boss, plan ready hai: {plan.goal}", ""]
        for step in plan.steps:
            lines.append(f"{step.number}. {step.title}")
        lines.append("")
        lines.append("Next: Step 1 se start karte hain.")
        return "\n".join(lines)
