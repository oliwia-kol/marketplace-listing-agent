import pytest

from marketplace_agent.domain.copy_pipeline import assess_draft, build_copy_brief
from marketplace_agent.domain.models import FactProposal, ItemFacts, PortalDraft


def approved_fact(name: str, value: str, **kwargs) -> FactProposal:
    return FactProposal(
        name=name,
        value=value,
        confidence=1,
        source=kwargs.pop("source", "user"),
        approved=True,
        **kwargs,
    )


def test_brief_separates_item_evidence_from_sourced_product_specification() -> None:
    brief = build_copy_brief(
        [
            approved_fact("model", "XF 23mm F2 R WR"),
            approved_fact("defects", "rysa na osłonie"),
            approved_fact(
                "attribute.mount",
                "Fujifilm X",
                source="manufacturer",
                scope="product_spec",
                source_url="https://example.test/manual",
                source_excerpt="Mocowanie Fujifilm X.",
            ),
        ],
        ["olx"],
    )

    by_key = {claim.key: claim for claim in brief.claims}
    assert by_key["defects"].scope == "item"
    assert by_key["attribute.mount"].scope == "product_spec"
    assert by_key["attribute.mount"].source_url == "https://example.test/manual"


def test_brief_keeps_category_as_copy_evidence() -> None:
    brief = build_copy_brief(
        [
            approved_fact("category", "lokówka"),
            approved_fact("brand", "Remington"),
            approved_fact("model", "CI9532"),
        ],
        ["olx"],
    )

    by_key = {claim.key: claim for claim in brief.claims}
    assert by_key["category"].value == "lokówka"
    assert by_key["category"].required


def test_product_specs_are_not_item_form_facts() -> None:
    facts = ItemFacts(
        proposals=[
            approved_fact("model", "Switch OLED"),
            approved_fact(
                "attribute.screen",
                "OLED 7 cali",
                source="manufacturer",
                scope="product_spec",
                source_url="https://example.test/spec",
            ),
        ]
    )

    assert facts.approved_dict(scope="item") == {"model": "Switch OLED"}


def test_product_spec_without_source_is_rejected() -> None:
    with pytest.raises(ValueError, match="source_url"):
        approved_fact("attribute.screen", "OLED 7 cali", scope="product_spec")


def test_assessment_accepts_polish_inflection_and_requires_disclosed_defect() -> None:
    brief = build_copy_brief(
        [
            approved_fact("model", "Fujifilm XF 23mm F2 R WR"),
            approved_fact("defects", "rysa na osłonie"),
        ],
        ["olx"],
    )
    safe = PortalDraft(
        portal="olx",
        title="Fujifilm XF 23mm F2 R WR",
        description="Na osłonie znajduje się drobna rysa.",
        category="Fotografia",
        price_pln=1000,
    )
    missing = safe.model_copy(update={"description": "Obiektyw w dobrym stanie wizualnym."})

    assert assess_draft(safe, brief).safe
    assert assess_draft(missing, brief).missing_required_keys == ["defects"]


def test_assessment_rejects_unverified_operability_claim() -> None:
    brief = build_copy_brief(
        [approved_fact("model", "Nintendo Switch Lite")],
        ["olx"],
    )
    draft = PortalDraft(
        portal="olx",
        title="Nintendo Switch Lite",
        description="Konsola jest w pełni sprawna.",
        category="Konsole",
        price_pln=500,
    )

    result = assess_draft(draft, brief)
    assert not result.safe
    assert "sprawn" in result.unsupported_claims
