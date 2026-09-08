from marketplace_agent.research.extractors import (
    _price_from_json_ld,
    _price_from_text,
    unwrap_search_url,
)


def test_prices_are_extracted_from_structured_and_visible_text() -> None:
    assert _price_from_json_ld([{"@type": "Offer", "price": "1 250,00"}]) == 1250
    assert _price_from_text("Cena: 1 250,50 zł") == 1250.5


def test_duckduckgo_redirect_is_unwrapped() -> None:
    url = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.olx.pl%2Fd%2Foferta%2Fabc"
    assert unwrap_search_url(url) == "https://www.olx.pl/d/oferta/abc"
