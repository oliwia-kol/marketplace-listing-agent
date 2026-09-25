from __future__ import annotations

import json
import re
from pathlib import Path

from marketplace_agent.domain.models import ComparableCandidate, PriceResearchSummary

ITEM_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")


def write_research_manifest(
    data_dir: Path,
    item_id: str,
    candidates: list[ComparableCandidate],
    summary: PriceResearchSummary,
) -> str:
    """Persist the evidence decision trail without HTML, prompts, cookies or secrets."""
    if ITEM_ID_PATTERN.fullmatch(item_id) is None:
        raise ValueError("item_id contains unsupported characters")
    relative_path = Path("items") / item_id / "evidence" / "research.json"
    target = data_dir / relative_path
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    target.parent.chmod(0o700)
    payload = {
        "schema_version": 1,
        "item_id": item_id,
        "generated_at": summary.generated_at.isoformat(),
        "summary": summary.model_dump(mode="json", exclude={"evidence_manifest_path"}),
        "candidates": [
            {
                "source": row.source,
                "url": str(row.url),
                "title": row.title,
                "price_amount": row.price_pln,
                "currency": row.currency,
                "price_kind": row.price_kind,
                "status": row.status,
                "verified": row.verified,
                "comparable": row.comparable,
                "match_score": row.match_score,
                "integrity_status": row.integrity_status,
                "integrity_reasons": row.integrity_reasons,
                "rejection_reason": row.rejection_reason,
                "rejection_codes": row.rejection_codes,
                "evidence_channels": row.evidence_channels,
                "checked_at": row.checked_at.isoformat(),
            }
            for row in candidates
        ],
    }
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.chmod(0o600)
    temporary.replace(target)
    target.chmod(0o600)
    return relative_path.as_posix()
