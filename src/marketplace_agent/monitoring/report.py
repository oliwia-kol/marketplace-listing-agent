from __future__ import annotations

import json
from collections import Counter
from html import escape
from pathlib import Path
from typing import Any


def write_run_report(events: list[dict[str, Any]], reports_dir: Path, run_id: str) -> Path:
    """Render a local HTML report from metadata-only events.

    Prompts, listing descriptions, image contents, tokens and cookies are never
    accepted by this renderer. Event payloads are reduced to a fixed allow-list.
    """

    reports_dir.mkdir(parents=True, exist_ok=True)
    allowed = {
        "model",
        "attempt",
        "fallback_used",
        "system_hash",
        "schema",
        "duration_seconds",
        "load_seconds",
        "prompt_tokens",
        "completion_tokens",
        "error_type",
    }
    counts = Counter(event["status"] for event in events)
    rows: list[str] = []
    for event in events:
        metadata = {key: value for key, value in event.get("payload", {}).items() if key in allowed}
        rows.append(
            "<tr>"
            f"<td>{escape(str(event.get('created_at', '')))}</td>"
            f"<td>{escape(str(event.get('component', '')))}</td>"
            f"<td>{escape(str(event.get('operation', '')))}</td>"
            f"<td>{escape(str(event.get('status', '')))}</td>"
            f"<td><code>{escape(json.dumps(metadata, ensure_ascii=False))}</code></td>"
            "</tr>"
        )
    body = f"""<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><title>Run {escape(run_id)}</title>
<style>
body{{font:16px system-ui;margin:2rem;max-width:1200px}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ccc;padding:.5rem;text-align:left;vertical-align:top}}
code{{white-space:pre-wrap}}
</style>
</head><body><h1>Przebieg {escape(run_id)}</h1>
<p>Zdarzenia: {len(events)}; OK: {counts["ok"]}; błędy: {counts["error"]}.</p>
<p>Raport zawiera metadane operacyjne. Nie zawiera promptów, opisów ofert ani obrazów.</p>
<table><thead><tr><th>Czas</th><th>Komponent</th><th>Operacja</th><th>Status</th><th>Metadane</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></body></html>"""
    path = reports_dir / f"run-{run_id}.html"
    path.write_text(body, encoding="utf-8")
    path.chmod(0o600)
    return path
