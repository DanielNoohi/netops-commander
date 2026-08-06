"""Export utilities (CSV, JSON, HTML)."""
import csv
import html
import json
from typing import Any, List


def _cell(value: Any) -> str:
    """Stringify a cell value for HTML with XSS-safe escaping."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def export_csv(filename: str, rows: List[dict]) -> None:
    if not rows:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("")
        return
    fieldnames = list(rows[0].keys())
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_json(filename: str, rows: List[dict]) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, default=str)


def export_html(filename: str, title: str, rows: List[dict]) -> None:
    safe_title = _cell(title)
    parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{safe_title}</title>",
        "<style>body{font-family:Segoe UI,Arial,sans-serif;background:#121212;color:#eee;padding:20px}"
        "table{border-collapse:collapse;width:100%}th,td{border:1px solid #444;padding:8px;text-align:left}"
        "th{background:#1f2937;color:#fff}</style></head><body>",
        f"<h1>{safe_title}</h1><table><tr>",
    ]
    if rows:
        for key in rows[0].keys():
            parts.append(f"<th>{_cell(key)}</th>")
        parts.append("</tr>")
        for row in rows:
            parts.append("<tr>")
            for v in row.values():
                parts.append(f"<td>{_cell(v)}</td>")
            parts.append("</tr>")
    parts.append("</table></body></html>")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("".join(parts))
