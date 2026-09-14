import json
from pathlib import Path

from scripts.build_blind_copy_review import build_packet


def _report(path: Path, model: str, title: str) -> None:
    path.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "case_id": "case-1",
                        "model": model,
                        "output": {
                            "drafts": [
                                {
                                    "portal": "olx",
                                    "title": title,
                                    "description": "Opis bez sekretów",
                                }
                            ]
                        },
                    }
                ]
            }
        )
    )


def test_blind_packet_hides_models_and_keeps_reveal_key(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    _report(first, "model-secret-a", "Wariant A")
    _report(second, "model-secret-b", "Wariant B")
    packet = tmp_path / "packet.html"
    key = tmp_path / "key.json"

    dataset = tmp_path / "dataset.jsonl"
    dataset.write_text(
        json.dumps({"id": "case-1", "input": {"facts": {"defects": "rysa"}}}) + "\n"
    )

    build_packet([first, second], packet, key, dataset_path=dataset)

    html = packet.read_text()
    assert "model-secret" not in html
    assert "localStorage" in html
    assert "Eksportuj oceny" in html
    assert "rysa" in html
    reveal = json.loads(key.read_text())["reveal"]
    assert {row["model"] for row in reveal} == {"model-secret-a", "model-secret-b"}
    assert packet.stat().st_mode & 0o777 == 0o600
    assert key.stat().st_mode & 0o777 == 0o600
