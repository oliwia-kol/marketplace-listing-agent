from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from marketplace_agent.domain.copy_safety import obvious_unsupported_claims
from marketplace_agent.domain.models import FactProposal, PortalDraft
from marketplace_agent.models.tasks import CopyBrief, CopyClaim, CopyTextDraft

DESCRIPTION_KEYS = {
    "brand",
    "model",
    "color",
    "condition",
    "defects",
    "size",
    "material",
    "dimensions",
    "completeness",
    "accessories",
    "identifiers",
}
CRITICAL_KEYS = {
    "category",
    "brand",
    "model",
    "defects",
    "completeness",
    "accessories",
    "identifiers",
}
PROHIBITED_CLAIMS = [
    "sprawność bez udokumentowanego testu egzemplarza",
    "brak innych wad",
    "akcesoria i kompletność nieobecne w briefie",
    "gwarancja lub dowód zakupu nieobecne w briefie",
    "stan baterii nieobecny w briefie",
    "dane kontaktowe, odbiór i dostawa nieobecne w briefie",
]


@dataclass(frozen=True, slots=True)
class DeterministicAssessment:
    safe: bool
    missing_required_keys: list[str]
    unsupported_claims: list[str]


def build_copy_brief(
    facts: list[FactProposal],
    portals: list[str],
    preferences: list[dict[str, Any]] | None = None,
) -> CopyBrief:
    claims: list[CopyClaim] = []
    for fact in facts:
        if not fact.approved or fact.value in (None, ""):
            continue
        claims.append(
            CopyClaim(
                key=fact.name,
                value=str(fact.value),
                scope=fact.scope,
                required=fact.name in CRITICAL_KEYS or fact.name.startswith("attribute."),
                source_url=str(fact.source_url) if fact.source_url else None,
                source_excerpt=fact.source_excerpt,
            )
        )
    return CopyBrief(
        claims=claims,
        portals=portals,  # type: ignore[arg-type]
        preferences=preferences or [],
        prohibited_claim_types=PROHIBITED_CLAIMS,
    )


def portal_draft_from_text(
    text: CopyTextDraft,
    *,
    facts: dict[str, Any],
    price_pln: float,
) -> PortalDraft:
    attributes = {
        key.removeprefix("attribute."): value
        for key, value in facts.items()
        if key.startswith("attribute.")
    }
    return PortalDraft(
        portal=text.portal,
        title=text.title.strip(),
        description=text.description.strip(),
        category=str(facts.get("category") or "Inne"),
        price_pln=price_pln,
        condition=str(facts["condition"]) if facts.get("condition") is not None else None,
        attributes=attributes,
        approved=False,
    )


def assess_draft(draft: PortalDraft, brief: CopyBrief) -> DeterministicAssessment:
    text = f"{draft.title} {draft.description}"
    missing = [
        claim.key
        for claim in brief.claims
        if claim.required and not _meaningfully_contains(text, claim.value)
    ]
    evidence = {claim.key: claim.value for claim in brief.claims}
    unsupported = obvious_unsupported_claims(draft, evidence)
    return DeterministicAssessment(
        safe=not missing and not unsupported,
        missing_required_keys=sorted(set(missing)),
        unsupported_claims=unsupported,
    )


def _meaningfully_contains(text: str, expected: str) -> bool:
    actual_tokens = _tokens(text)
    expected_tokens = _tokens(expected)
    if not expected_tokens:
        return True
    return all(
        any(_tokens_match(wanted, actual) for actual in actual_tokens)
        for wanted in expected_tokens
    )


def _tokens(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.findall(r"[\w]+", normalized, flags=re.UNICODE)


def _tokens_match(expected: str, actual: str) -> bool:
    if expected == actual:
        return True
    if expected.isdigit() or actual.isdigit() or min(len(expected), len(actual)) < 5:
        return False
    return expected[:4] == actual[:4]
