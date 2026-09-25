from __future__ import annotations

import json
from collections import Counter
from html import escape
from pathlib import Path
from statistics import fmean
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


def write_copy_report(
    diagnostics: list[dict[str, Any]],
    reports_dir: Path,
    run_id: str,
    ratings: list[dict[str, Any]] | None = None,
) -> Path:
    """Render locally retained copy, evidence and audit stages for one run."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    stages = Counter(str(row.get("stage", "unknown")) for row in diagnostics)
    final_rows = [row for row in diagnostics if row.get("stage") == "final"]
    warning_count = sum(
        len(row.get("payload", {}).get("warnings", []))
        for row in final_rows
        if isinstance(row.get("payload"), dict)
    )
    ratings = ratings or []
    score_names = ("naturalness", "clarity", "factual_trust", "portal_fit", "usefulness")
    rating_summary = {
        name: round(fmean(float(row[name]) for row in ratings), 2)
        for name in score_names
        if ratings
    }
    rows = []
    for row in diagnostics:
        payload = escape(json.dumps(row.get("payload", {}), ensure_ascii=False, indent=2))
        rows.append(
            "<section>"
            f"<h2>{escape(str(row.get('stage', '')))}</h2>"
            f"<p>Portal: {escape(str(row.get('portal') or 'wspólny'))}; "
            f"czas: {escape(str(row.get('created_at', '')))}; "
            f"hash: <code>{escape(str(row.get('payload_sha256', '')))}</code></p>"
            f"<pre>{payload}</pre>"
            "</section>"
        )
    body = f"""<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><title>Copy run {escape(run_id)}</title>
<style>
body{{font:16px system-ui;margin:2rem;max-width:1000px}}
section{{border:1px solid #ccc;border-radius:8px;padding:1rem;margin:1rem 0}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f6f6f6;padding:1rem}}
</style></head><body><h1>Przebieg opisu {escape(run_id)}</h1>
<p>Treść diagnostyczna jest lokalna, zredagowana z typowych sekretów i wygasa po 30 dniach.</p>
<p>Etapy: {escape(json.dumps(stages, ensure_ascii=False))};
finalne ostrzeżenia: {warning_count}.</p>
<p>Oceny człowieka: {len(ratings)};
średnie: {escape(json.dumps(rating_summary, ensure_ascii=False))}.</p>
{"".join(rows)}</body></html>"""
    path = reports_dir / f"copy-{run_id}.html"
    path.write_text(body, encoding="utf-8")
    path.chmod(0o600)
    return path
