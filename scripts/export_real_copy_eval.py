from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_SOURCE = ROOT / "data" / "private_eval_sources_2026-09-14.jsonl"
PUBLIC_DATASET = ROOT / "goldens" / "copy_real_anonymized.jsonl"
ALLOWED_SOURCE_KEYS = {"id", "url", "portal", "facts"}
FORBIDDEN_FACT_KEYS = {"seller", "seller_name", "location", "phone", "email", "price"}
PORTAL_HOSTS = {
    "olx": {"olx.pl", "www.olx.pl"},
    "allegro_lokalnie": {"allegrolokalnie.pl", "www.allegrolokalnie.pl"},
}


def load_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def export(source: Path = PRIVATE_SOURCE, destination: Path = PUBLIC_DATASET) -> int:
    rows = load_rows(source)
    output: list[dict[str, Any]] = []
    for row in rows:
        unexpected = set(row) - ALLOWED_SOURCE_KEYS
        if unexpected:
            raise ValueError(f"{row.get('id')}: unexpected private keys {sorted(unexpected)}")
        parsed = urlsplit(row["url"])
        allowed_hosts = PORTAL_HOSTS.get(row["portal"], set())
        if (
            parsed.scheme != "https"
            or parsed.hostname not in allowed_hosts
            or parsed.username
            or parsed.password
        ):
            raise ValueError(f"{row['id']}: URL does not match the declared marketplace")
        facts = row["facts"]
        forbidden = FORBIDDEN_FACT_KEYS & set(facts)
        if forbidden:
            raise ValueError(f"{row['id']}: personal or commercial fields {sorted(forbidden)}")
        canonical_url = parsed._replace(query="", fragment="").geturl()
        url_hash = hashlib.sha256(canonical_url.encode()).hexdigest()
        output.append(
            {
                "id": row["id"],
                "split": "real_validation",
                "source_portal": row["portal"],
                "source_url_sha256": url_hash,
                "observed_at": "2026-09-14",
                "input": {
                    "facts": facts,
                    "portals": [row["portal"]],
                    "price_pln": 1,
                    "preferences": [{"style": "naturalny i konkretny"}],
                },
                "required_phrases": [],
                "forbidden_phrases": ["fabrycznie nowy", "wieczysta gwarancja"],
                "provenance": "public_listing_claims_anonymized_v1",
                "evidence_limit": (
                    "Facts are normalized seller assertions from a public listing; "
                    "they are not independent proof of item condition or operability."
                ),
                "annotation_method": "model_assisted_manual_normalization_single_reviewer",
            }
        )
    destination.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in output
        ),
        encoding="utf-8",
    )
    return len(output)


def main() -> None:
    print(f"exported={export()}")


if __name__ == "__main__":
    main()
