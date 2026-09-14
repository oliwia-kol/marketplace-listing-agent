import json
from pathlib import Path

import pytest

from scripts.export_real_copy_eval import export


def test_real_copy_dataset_is_anonymized_and_source_hashed() -> None:
    rows = [
        json.loads(line)
        for line in Path("goldens/copy_real_anonymized.jsonl").read_text().splitlines()
    ]

    assert len(rows) == 30
    assert all(row["split"] == "real_validation" for row in rows)
    assert all(len(row["source_url_sha256"]) == 64 for row in rows)
    rendered = json.dumps(rows, ensure_ascii=False).casefold()
    assert "https://" not in rendered
    assert "seller_name" not in rendered
    assert "location" not in rendered
    assert "@" not in rendered


def test_real_copy_export_rejects_wrong_domain(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    source.write_text(
        json.dumps(
            {
                "id": "bad-source",
                "url": "https://example.test/pretends-to-be-olx",
                "portal": "olx",
                "facts": {"model": "test"},
            }
        )
    )

    with pytest.raises(ValueError, match="declared marketplace"):
        export(source, tmp_path / "output.jsonl")
