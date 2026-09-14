from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from marketplace_agent.domain.copy_pipeline import (
    assess_draft,
    build_copy_brief,
    portal_draft_from_text,
)
from marketplace_agent.domain.models import FactProposal
from marketplace_agent.models.tasks import CopyTextDraft


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def score_case(row: dict[str, Any], output: dict[str, Any]) -> dict[str, float]:
    facts = row["input"]["facts"]
    brief = build_copy_brief(
        [
            FactProposal(
                name=name,
                value=value,
                confidence=1,
                source="user",
                approved=True,
            )
            for name, value in facts.items()
        ],
        row["input"]["portals"],
        row["input"].get("preferences", []),
    )
    drafts = [
        portal_draft_from_text(
            CopyTextDraft.model_validate(value),
            facts=facts,
            price_pln=float(row["input"]["price_pln"]),
        )
        for value in output["drafts"]
    ]
    assessments = [assess_draft(draft, brief) for draft in drafts]
    required_count = sum(claim.required for claim in brief.claims) * len(drafts)
    missing_count = sum(len(value.missing_required_keys) for value in assessments)
    text = " ".join(f"{draft.title} {draft.description}" for draft in drafts).casefold()
    forbidden = [value.casefold() for value in row["forbidden_phrases"]]
    return {
        "required_fact_recall": 1 - missing_count / required_count if required_count else 1.0,
        "hallucination_guard": float(
            not any(value in text for value in forbidden)
            and not any(value.unsupported_claims for value in assessments)
        ),
        "exact_portals": float({draft.portal for draft in drafts} == set(row["input"]["portals"])),
        "schema_valid": 1.0,
    }


def rescore(report_path: Path, dataset_path: Path, destination: Path | None = None) -> Path:
    source_bytes = report_path.read_bytes()
    report = json.loads(source_bytes)
    cases = {row["id"]: row for row in load_jsonl(dataset_path)}
    for result in report["results"]:
        base_id = result["case_id"].split("#run-", 1)[0]
        if result["output"] is None or base_id not in cases:
            continue
        result["metrics_before_rescore"] = result["metrics"]
        result["metrics"] = score_case(cases[base_id], result["output"])
        result["passed"] = all(value + 1e-9 >= 0.8 for value in result["metrics"].values())
    metric_names = sorted({name for result in report["results"] for name in result["metrics"]})
    report["passed"] = sum(result["passed"] for result in report["results"])
    report["total"] = len(report["results"])
    report["pass_rate"] = report["passed"] / report["total"]
    report["aggregate_metrics"] = {
        name: statistics.fmean(result["metrics"].get(name, 0.0) for result in report["results"])
        for name in metric_names
    }
    try:
        scorer_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=3
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        scorer_commit = "unavailable"
    report["rescore"] = {
        "rescored_at": datetime.now(UTC).isoformat(),
        "source_report_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "scorer_git_commit": scorer_commit,
    }
    destination = destination or report_path.with_name(f"{report_path.stem}-rescored.json")
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Rescore stored copy outputs without inference.")
    parser.add_argument("report", type=Path)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    print(rescore(args.report, args.dataset, args.destination))


if __name__ == "__main__":
    main()
