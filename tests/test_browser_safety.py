import pytest

from marketplace_agent.browser.forms import (
    _is_publish_target,
    _is_safe_click_target,
    _json_safe_form_value,
)
from marketplace_agent.research.sources import canonicalize_listing_url, host_matches_domain


@pytest.mark.parametrize(
    "label", ["Opublikuj ogłoszenie", "WYSTAW", "Sprzedaj teraz", "Publish listing", "Submit"]
)
def test_publication_words_are_blocked(label: str) -> None:
    assert _is_publish_target(label)


@pytest.mark.parametrize("label", ["Kategoria", "Dodaj zdjęcie", "Dalej", "Cena"])
def test_normal_form_targets_are_allowed(label: str) -> None:
    assert not _is_publish_target(label)


def test_ai_clicks_use_a_small_allowlist() -> None:
    assert _is_safe_click_target("Wybierz kategorię")
    assert not _is_safe_click_target("Dalej")
    assert not _is_safe_click_target("Zapisz i opublikuj")
    assert not _is_safe_click_target("Kategoria i opublikuj później")


def test_photo_paths_are_redacted_and_json_serializable() -> None:
    import json
    from pathlib import Path

    safe = _json_safe_form_value({"photos": [Path("/private/secret/item.jpg")]})
    assert json.dumps(safe) == '{"photos": [{"file_name": "item.jpg"}]}'


def test_marketplace_domain_matching_does_not_accept_substring_attacks() -> None:
    assert host_matches_domain("www.olx.pl", "olx.pl")
    assert host_matches_domain("sub.allegrolokalnie.pl", "allegrolokalnie.pl")
    assert not host_matches_domain("olx.pl.evil.example", "olx.pl")
    assert not host_matches_domain("fake-olx.pl", "olx.pl")


def test_listing_urls_are_canonicalized_before_deduplication() -> None:
    assert canonicalize_listing_url(
        "https://www.OLX.pl/d/oferta/test/?utm_source=x#details"
    ) == "https://olx.pl/d/oferta/test"
