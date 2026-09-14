import json
from collections import Counter
from pathlib import Path


def test_generalization_dataset_has_category_level_splits() -> None:
    rows = [
        json.loads(line)
        for line in Path("goldens/copy_generalization.jsonl").read_text().splitlines()
    ]

    assert len(rows) == 120
    assert Counter(row["split"] for row in rows) == {
        "development": 40,
        "selection": 40,
        "frozen": 40,
    }
    family_splits: dict[str, set[str]] = {}
    for row in rows:
        family_splits.setdefault(row["family_id"], set()).add(row["split"])
    assert len(family_splits) == 12
    assert all(len(splits) == 1 for splits in family_splits.values())
    assert {row["family_id"] for row in rows if row["split"] == "frozen"} == {
        "router",
        "mixer",
        "dryer",
        "drill",
    }
