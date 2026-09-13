from marketplace_agent.domain.copy_safety import obvious_unsupported_claims, safe_template
from marketplace_agent.domain.models import PortalDraft


def test_guard_finds_unsupported_dimensions_and_functionality() -> None:
    draft = PortalDraft(
        portal="olx",
        title="IKEA FADO lampa stojąca",
        description="Sprawna. Wysokość 150 cm.",
        category="Dom",
        price_pln=70,
    )
    findings = obvious_unsupported_claims(draft, {"brand": "IKEA", "model": "FADO"})
    assert "sprawn" in findings
    assert "stojąc" in findings
    assert "nieznana liczba: 150" in findings


def test_safe_template_uses_only_approved_values() -> None:
    draft = PortalDraft(
        portal="vinted",
        title="unsafe",
        description="unsafe",
        category="Odzież damska",
        price_pln=120,
    )
    result = safe_template(
        draft,
        {"category": "płaszcz damski", "material": "wełna", "size": "M"},
    )
    assert result.title == "płaszcz damski - M"
    assert "Materiał: wełna." in result.description
    assert "Stan" not in result.description


def test_guard_catches_benchmark_accessory_and_operability_inventions() -> None:
    draft = PortalDraft(
        portal="olx",
        title="Nintendo Switch Lite",
        description=(
            "W pełni sprawna, wszystkie funkcje działają bez zarzutu. "
            "W zestawie ładowarka i kabel HDMI."
        ),
        category="Elektronika",
        price_pln=500,
    )
    findings = obvious_unsupported_claims(
        draft,
        {"brand": "Nintendo", "model": "Switch Lite", "defects": "otarcie obudowy"},
    )

    assert {"sprawn", "wszystkie funkcje", "bez zarzutu", "ładowark", "kabel", "hdmi"} <= set(
        findings
    )
