import pytest

from marketplace_agent.browser.forms import _is_publish_target, _is_safe_click_target


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
