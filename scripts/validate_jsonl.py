from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate_jsonl(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    seen_ids: dict[str, Path] = {}
    for path in paths:
        if not path.is_file():
            errors.append(f"missing file: {path}")
            continue
        for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                errors.append(f"{path}:{line_number}: blank line")
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as error:
                errors.append(f"{path}:{line_number}: invalid JSON: {error.msg}")
                continue
            if not isinstance(row, dict):
                errors.append(f"{path}:{line_number}: expected object")
                continue
            case_id = row.get("id")
            if not isinstance(case_id, str) or not case_id.strip():
                errors.append(f"{path}:{line_number}: missing string id")
            elif case_id in seen_ids:
                errors.append(f"{path}:{line_number}: duplicate id also in {seen_ids[case_id]}")
            else:
                seen_ids[case_id] = path
            required = (
                {"notes", "expected_fields"}
                if path.name == "facts.jsonl"
                else {"candidates", "expected"}
                if path.name == "price_math.jsonl"
                else {"input"}
            )
            for key in sorted(required - row.keys()):
                errors.append(f"{path}:{line_number}: missing {key}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate golden JSONL files.")
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    paths = args.paths or sorted(Path("goldens").glob("*.jsonl"))
    errors = validate_jsonl(paths)
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
