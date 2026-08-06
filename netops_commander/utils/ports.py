"""Helpers for open_ports stored as JSON text on Device ORM rows."""
from __future__ import annotations

import json
from typing import Any, List


def parse_open_ports(value: Any) -> List[int]:
    """Normalize open_ports from DB/UI into a list of ints.

    DB model stores JSON text via json.dumps(...). Callers must never treat
    the ORM attribute as a list directly.
    """
    if value is None or value == "":
        return []
    if isinstance(value, list):
        out: List[int] = []
        for item in value:
            try:
                out.append(int(item))
            except (TypeError, ValueError):
                continue
        return out
    if isinstance(value, (tuple, set)):
        return parse_open_ports(list(value))
    if isinstance(value, int):
        return [value]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            return parse_open_ports(parsed)
        except json.JSONDecodeError:
            # Fallback: "80,443" or "80|443"
            parts = [p.strip() for p in text.replace("|", ",").split(",") if p.strip()]
            out = []
            for p in parts:
                try:
                    out.append(int(p))
                except ValueError:
                    continue
            return out
    return []


def format_open_ports(value: Any, sep: str = ", ") -> str:
    """Human-readable ports string for tables/exports."""
    ports = parse_open_ports(value)
    return sep.join(str(p) for p in ports)
