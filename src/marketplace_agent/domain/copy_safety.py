from __future__ import annotations

import re
from typing import Any

from marketplace_agent.domain.category_profiles import redact_sensitive_facts
from marketplace_agent.domain.models import PortalDraft

RISKY_CLAIMS = (
    "idealn",
    "bez wad",
    "bez ślad",
    "sprawn",
    "działa",
    "bez zarzutu",
    "gotow",
    "wszystkie funkcje",
    "jedyną wad",
    "nie wpływa na",
    "kompletn",
    "pudełk",
    "opakowanie",
    "ładowark",
    "bateri",
    "kabel",
    "hdmi",
    "odbiór osobisty",
    "do kolan",
    "guzik",
    "podszew",
    "klasyczny krój",
    "stojąc",
)

POLISH_LABELS = {
    "category": "Przedmiot",
    "brand": "Marka",
    "model": "Model",
    "color": "Kolor",
    "condition": "Stan",
    "defects": "Wady",
    "size": "Rozmiar",
    "material": "Materiał",
    "dimensions": "Wymiary",
    "completeness": "Kompletność",
    "accessories": "Akcesoria",
    "identifiers": "Identyfikatory",
}


def obvious_unsupported_claims(draft: PortalDraft, facts: dict[str, Any]) -> list[str]:
    text = f"{draft.title} {draft.description}".casefold()
    evidence = " ".join(str(value) for value in facts.values()).casefold()
    findings = [
        claim
        for claim in RISKY_CLAIMS
        if claim in text and not _risky_claim_supported(claim, facts, evidence)
    ]
    evidence_numbers = set(re.findall(r"\d+(?:[,.]\d+)?", evidence))
    text_numbers = set(re.findall(r"\d+(?:[,.]\d+)?", text))
    allowed_numbers = evidence_numbers | {str(int(draft.price_pln)), str(draft.price_pln)}
    findings.extend(f"nieznana liczba: {number}" for number in text_numbers - allowed_numbers)
    return sorted(set(findings))


def _risky_claim_supported(claim: str, facts: dict[str, Any], evidence: str) -> bool:
    if claim in evidence:
        return True
    keys = {key.casefold() for key in facts}
    if claim == "bateri":
        return any("battery" in key or "bateria" in key for key in keys)
    if claim in {"sprawn", "działa", "bez zarzutu", "gotow", "wszystkie funkcje"}:
        return any("test_claim" in key for key in keys)
    if claim in {"pudełk", "opakowanie"}:
        return any(token in evidence for token in ("pudeł", "karton", "opakowanie"))
    if claim == "ładowark":
        return any(token in evidence for token in ("ładowark", "zasilacz"))
    if claim == "kabel":
        return any(token in evidence for token in ("kabel", "przewód"))
    return False


def safe_template(draft: PortalDraft, facts: dict[str, Any]) -> PortalDraft:
    facts = redact_sensitive_facts(facts)
    headline_keys = ("brand", "model", "category", "color", "size")
    parts: list[str] = []
    for key in headline_keys:
        value = facts.get(key)
        if value is not None and str(value).casefold() not in {part.casefold() for part in parts}:
            parts.append(str(value))
    title = " - ".join(parts)[:70] or "Przedmiot na sprzedaż"
    lines = []
    for key, value in facts.items():
        if value in (None, ""):
            continue
        label = POLISH_LABELS.get(key, key.removeprefix("attribute.").replace("_", " ").title())
        lines.append(f"{label}: {value}.")
    return PortalDraft(
        portal=draft.portal,
        title=title,
        description="\n".join(lines),
        category=draft.category,
        price_pln=draft.price_pln,
        condition=draft.condition,
        sale_type=draft.sale_type,
        location=draft.location,
        delivery=draft.delivery,
        attributes=draft.attributes,
        approved=False,
    )
