from pathlib import Path

from marketplace_agent.domain.category_profiles import (
    CategoryProfileCatalog,
    redact_sensitive_facts,
)
from marketplace_agent.domain.copy_safety import safe_template
from marketplace_agent.domain.models import FactProposal, PortalDraft


def catalog() -> CategoryProfileCatalog:
    root = Path(__file__).resolve().parents[1]
    return CategoryProfileCatalog.from_yaml(root / "config" / "category_profiles.yaml")


def test_profile_matches_lens_and_supplies_variant_traps() -> None:
    profile = catalog().match(
        {"category": "obiektyw", "brand": "Fujifilm", "model": "XF 23mm F1.4 R"}
    )
    assert profile is not None
    assert profile.id == "fujifilm_x_lens"
    assert any("XF" in trap and "XC" in trap for trap in profile.variant_traps)


def test_sensitive_identifiers_are_removed_from_research_facts() -> None:
    profile = catalog().match({"category": "MacBook", "brand": "Apple"})
    assert profile is not None
    safe = profile.research_facts(
        {
            "brand": "Apple",
            "model": "MacBook Air M2",
            "identifiers": "TEST-SERIAL-DO-NOT-PUBLISH",
            "attribute.imei": "123456789",
        }
    )
    assert safe == {"brand": "Apple", "model": "MacBook Air M2"}
    assert "identifiers" not in redact_sensitive_facts({"identifiers": "SECRET", "brand": "Apple"})


def test_switch_console_and_game_profiles_are_not_confused() -> None:
    profiles = catalog()
    console = profiles.match({"category": "konsola", "brand": "Nintendo", "model": "Switch OLED"})
    game = profiles.match(
        {
            "category": "gra",
            "brand": "Nintendo",
            "model": "Zelda",
            "user_context": "gra na Nintendo Switch, kartridż",
        }
    )
    assert console is not None and console.id == "nintendo_switch_console"
    assert game is not None and game.id == "nintendo_switch_game"


def test_reserved_attribute_name_is_normalized_and_secret_not_copied() -> None:
    fact = FactProposal(name="attribute.model", value="MacBook Air", confidence=1, source="model")
    assert fact.name == "model"
    draft = PortalDraft(
        portal="olx", title="draft", description="draft", category="Elektronika", price_pln=1
    )
    rendered = safe_template(
        draft,
        {
            "brand": "Apple",
            "model": "MacBook Air",
            "identifiers": "TEST-SERIAL-DO-NOT-PUBLISH",
        },
    )
    assert "TEST-SERIAL-DO-NOT-PUBLISH" not in rendered.description
