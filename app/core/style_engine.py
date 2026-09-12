import json
from pathlib import Path


class StyleEngine:
    """Lightweight retrieval of conversational examples for MIRA's response style."""

    def __init__(self, dataset_path: str = "docs/mira_style_dataset.jsonl"):
        self.path = Path(dataset_path)
        self.examples = self._load()

    def _load(self):
        if not self.path.exists():
            return []
        examples = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if item.get("user") and item.get("assistant"):
                    examples.append(item)
            except json.JSONDecodeError:
                continue
        return examples

    def _score(self, message: str, item: dict) -> int:
        text = message.lower()
        user = item.get("user", "").lower()
        score = 0
        for token in user.replace("?", " ").replace(",", " ").split():
            if len(token) > 2 and token in text:
                score += 1
        category = item.get("category", "").lower()
        if category and category in text:
            score += 2
        return score

    def examples_for(self, message: str, limit: int = 3) -> str:
        if not self.examples:
            return ""
        ranked = sorted(self.examples, key=lambda x: self._score(message, x), reverse=True)
        selected = [x for x in ranked[:limit] if self._score(message, x) > 0]
        if not selected:
            selected = self.examples[:limit]
        lines = ["CONVERSATIONAL STYLE EXAMPLES:"]
        for item in selected:
            lines.append(f'Boss: {item["user"]}')
            lines.append(f'MIRA: {item["assistant"]}')
        return "\n".join(lines)
