from __future__ import annotations

import argparse
import hashlib
import html
import json
import random
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _base_case_id(value: str) -> str:
    return value.split("#run-", 1)[0]


def build_packet(
    report_paths: list[Path],
    packet_path: Path,
    key_path: Path,
    *,
    seed: int = 42,
) -> tuple[Path, Path]:
    reports = [(path, _load_json(path)) for path in report_paths]
    if len(reports) < 2:
        raise ValueError("At least two reports are required")
    by_report = [
        {_base_case_id(row["case_id"]): row for row in report["results"] if row.get("output")}
        for _, report in reports
    ]
    shared_ids = sorted(set.intersection(*(set(rows) for rows in by_report)))
    if not shared_ids:
        raise ValueError("Reports have no shared cases")

    rng = random.Random(seed)
    cases: list[dict[str, Any]] = []
    reveal: list[dict[str, str]] = []
    for case_id in shared_ids:
        candidates = []
        for report_index, ((report_path, _), rows) in enumerate(
            zip(reports, by_report, strict=True)
        ):
            row = rows[case_id]
            opaque = hashlib.sha256(f"{seed}:{case_id}:{report_index}".encode()).hexdigest()[:10]
            candidates.append(
                {
                    "candidate_id": opaque,
                    "drafts": row["output"]["drafts"],
                }
            )
            reveal.append(
                {
                    "case_id": case_id,
                    "candidate_id": opaque,
                    "model": row["model"],
                    "report": str(report_path),
                    "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
                }
            )
        rng.shuffle(candidates)
        cases.append({"case_id": case_id, "candidates": candidates})

    packet = {
        "protocol": "blind_copy_review_v1",
        "seed": seed,
        "rating_scale": {
            "naturalness": "1 = sztuczny/szablonowy, 5 = naturalny język sprzedającego",
            "clarity": "1 = chaotyczny, 5 = od razu wiadomo co jest sprzedawane",
            "factual_trust": (
                "1 = budzi podejrzenia, 5 = wszystkie twierdzenia wyglądają na podparte"
            ),
            "portal_fit": "1 = nie pasuje, 5 = pasuje do polskiej oferty lokalnej",
            "usefulness": "1 = wymaga przepisania, 5 = gotowy po drobnej korekcie",
            "safety_veto": (
                "TAK, jeśli opis wymyśla stan, sprawność, komplet, parametry lub warunki sprzedaży"
            ),
        },
        "cases": cases,
    }
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(_render_html(packet))
    key_path.write_text(json.dumps({"protocol": packet["protocol"], "reveal": reveal}, indent=2))
    packet_path.chmod(0o600)
    key_path.chmod(0o600)
    return packet_path, key_path


def _render_html(packet: dict[str, Any]) -> str:
    sections = []
    for case in packet["cases"]:
        cards = []
        for index, candidate in enumerate(case["candidates"], start=1):
            drafts = []
            for draft in candidate["drafts"]:
                drafts.append(
                    f"<h4>{html.escape(str(draft['portal']))}: "
                    f"{html.escape(str(draft['title']))}</h4>"
                    f"<p>{html.escape(str(draft['description'])).replace(chr(10), '<br>')}</p>"
                )
            metrics = (
                ("naturalness", "naturalność"),
                ("clarity", "jasność"),
                ("factual_trust", "wiarygodność"),
                ("portal_fit", "dopasowanie"),
                ("usefulness", "użyteczność"),
            )
            fields = "".join(
                f'<label>{label}: <input data-metric="{metric}" '
                'type="number" min="1" max="5" /></label>'
                for metric, label in metrics
            )
            cards.append(
                f'<article data-case="{html.escape(case["case_id"])}" '
                f'data-candidate="{candidate["candidate_id"]}">'
                f"<h3>Wariant {index}</h3>{''.join(drafts)}"
                f'<div class="scores">{fields}</div>'
                '<label>Veto bezpieczeństwa: <input data-metric="safety_veto" '
                'type="checkbox" /></label>'
                '<label>Uwagi: <textarea data-metric="notes" rows="3"></textarea></label>'
                "</article>"
            )
        sections.append(
            f"<section><h2>{html.escape(case['case_id'])}</h2>{''.join(cards)}</section>"
        )
    return f"""<!doctype html>
<html lang="pl"><meta charset="utf-8"><title>Ślepa ocena opisów</title>
<style>
body{{font:16px system-ui;max-width:1100px;margin:auto;padding:24px;
background:#f5f5f2;color:#17211b}}
section{{border-top:3px solid #315c47;margin:36px 0}}
article{{background:white;padding:20px;margin:16px 0;border-radius:12px}}
.scores{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}}
label{{display:block;margin:10px 0}}input[type=number]{{width:48px}}
textarea{{display:block;width:100%}}
</style>
<h1>Ślepa ocena opisów ofert</h1>
<p>Najpierw oceń wszystkie warianty. Klucz modeli otwórz dopiero po zapisaniu
punktów. Skala 1-5; veto zaznacz przy każdym niepodpartym twierdzeniu.</p>
<button id="export">Eksportuj oceny do JSON</button>
{"".join(sections)}
<script>
const storageKey = "blind-copy-review-{packet["seed"]}";
const controls = [...document.querySelectorAll("[data-metric]")];
function collect() {{
  const grouped = {{}};
  for (const control of controls) {{
    const card = control.closest("article");
    const key = `${{card.dataset.case}}:${{card.dataset.candidate}}`;
    grouped[key] ||= {{case_id: card.dataset.case, candidate_id: card.dataset.candidate}};
    grouped[key][control.dataset.metric] = control.type === "checkbox"
      ? control.checked : control.value;
  }}
  return Object.values(grouped);
}}
function save() {{ localStorage.setItem(storageKey, JSON.stringify(collect())); }}
for (const control of controls) control.addEventListener("input", save);
const saved = JSON.parse(localStorage.getItem(storageKey) || "[]");
for (const row of saved) {{
  const card = document.querySelector(
    `article[data-case="${{row.case_id}}"][data-candidate="${{row.candidate_id}}"]`
  );
  if (!card) continue;
  for (const control of card.querySelectorAll("[data-metric]")) {{
    const value = row[control.dataset.metric];
    if (control.type === "checkbox") control.checked = Boolean(value);
    else control.value = value || "";
  }}
}}
document.querySelector("#export").addEventListener("click", () => {{
  const result = {{protocol: "blind_copy_review_v1", ratings: collect()}};
  const blob = new Blob(
    [JSON.stringify(result, null, 2)], {{type: "application/json"}}
  );
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob); link.download = "blind-copy-ratings.json"; link.click();
  URL.revokeObjectURL(link.href);
}});
</script></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a model-blind copy review packet.")
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--key", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    packet, key = build_packet(args.reports, args.packet, args.key, seed=args.seed)
    print(packet)
    print(key)


if __name__ == "__main__":
    main()
