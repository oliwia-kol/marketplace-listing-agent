import json

from experiments.lora.generate_dataset import generate


def test_lora_dataset_is_reproducible_and_family_split(tmp_path) -> None:
    counts = generate(tmp_path)
    assert counts == {"train": 240, "valid": 30, "test": 30}
    families = {}
    ids = set()
    for split in counts:
        rows = [json.loads(line) for line in (tmp_path / f"{split}.jsonl").read_text().splitlines()]
        for row in rows:
            assert row["id"] not in ids
            ids.add(row["id"])
            assert row["family_id"] not in families or families[row["family_id"]] == split
            families[row["family_id"]] = split
            assistant = row["messages"][-1]["content"]
            assert row["facts"]["defects"] in assistant
            assert row["provenance"] == "synthetic_rule_generated_v1"
