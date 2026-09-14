import json
from collections import Counter
from pathlib import Path


def test_lora_v2_dataset_is_split_by_unseen_product_family() -> None:
    root = Path("experiments/lora_v2/data")
    rows = {
        split: [json.loads(line) for line in (root / f"{split}.jsonl").read_text().splitlines()]
        for split in ("train", "valid", "test")
    }

    assert {split: len(values) for split, values in rows.items()} == {
        "train": 400,
        "valid": 100,
        "test": 100,
    }
    families = {split: {row["family_id"] for row in values} for split, values in rows.items()}
    assert families["train"].isdisjoint(families["valid"] | families["test"])
    assert families["valid"].isdisjoint(families["test"])
    assert Counter(row["provenance"] for values in rows.values() for row in values) == {
        "project_authored_synthetic_lora_v2": 600
    }
