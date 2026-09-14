from __future__ import annotations

import json
import statistics
from pathlib import Path

from scoring import score

ROOT = Path(__file__).parent


def rescore(report_path: Path, data_path: Path) -> None:
    report = json.loads(report_path.read_text())
    facts = {row["id"]: row["facts"] for row in map(json.loads, data_path.read_text().splitlines())}
    for row in report["results"]:
        row["metrics"] = score(row["output"], facts[row["id"]])
    names = report["results"][0]["metrics"]
    report["metrics"] = {
        name: statistics.fmean(row["metrics"][name] for row in report["results"])
        for name in names
    }
    report["scorer_version"] = "lora_v2_semantic_surface_v2"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    for name in ("base", "rank8", "rank16"):
        rescore(ROOT / "results" / f"{name}.json", ROOT / "data" / "test.jsonl")
