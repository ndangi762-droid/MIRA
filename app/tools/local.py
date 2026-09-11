"""Allowlisted local tools for MIRA.

File operations are restricted to MIRA_WORKSPACE. No arbitrary shell execution
is exposed through this module.
"""
from __future__ import annotations

import ast
import operator
import os
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(os.getenv("MIRA_WORKSPACE", "data/mira_workspace")).resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)

_BIN = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _calc(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        left, right = _calc(node.left), _calc(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("power too large")
        return _BIN[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_calc(node.operand))
    raise ValueError("only basic arithmetic is allowed")


def calculator(expression: str):
    tree = ast.parse(expression.strip(), mode="eval")
    value = _calc(tree.body)
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return {"ok": True, "expression": expression, "result": value}


def _safe_path(name: str) -> Path:
    raw = (WORKSPACE / name).resolve()
    if raw != WORKSPACE and WORKSPACE not in raw.parents:
        raise ValueError("path outside MIRA workspace is not allowed")
    return raw


def list_files():
    items = []
    for p in sorted(WORKSPACE.rglob("*")):
        if p.is_file():
            items.append(str(p.relative_to(WORKSPACE)))
    return {"ok": True, "workspace": str(WORKSPACE), "files": items[:500]}


def write_note(name: str, content: str):
    name = name.strip()
    if not name:
        raise ValueError("note name is required")
    p = _safe_path(name)
    if p.suffix.lower() not in {".txt", ".md"}:
        p = p.with_suffix(".md")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"ok": True, "saved": str(p.relative_to(WORKSPACE))}


def read_file(name: str):
    p = _safe_path(name.strip())
    if not p.is_file():
        raise FileNotFoundError(name)
    return {"ok": True, "file": str(p.relative_to(WORKSPACE)), "content": p.read_text(encoding="utf-8", errors="replace")[:50000]}


def search_files(query: str):
    q = query.lower().strip()
    if not q:
        raise ValueError("search query is required")
    hits = []
    for p in WORKSPACE.rglob("*"):
        if not p.is_file() or p.stat().st_size > 2_000_000:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if q in text.lower() or q in p.name.lower():
            hits.append(str(p.relative_to(WORKSPACE)))
            if len(hits) >= 100:
                break
    return {"ok": True, "query": query, "matches": hits}


def current_time():
    return {"ok": True, "iso": datetime.now().astimezone().isoformat()}
