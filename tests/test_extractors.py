from marketplace_agent.research.extractors import (
    _price_from_json_ld,
    _price_from_text,
    _price_integrity_reasons,
    _price_observations_from_json_ld,
    _price_observations_from_text,
    _select_item_price,
    unwrap_search_url,
)


def test_prices_are_extracted_from_structured_and_visible_text() -> None:
    assert _price_from_json_ld([{"@type": "Offer", "price": "1 250,00"}]) == 1250
    assert _price_from_text("Cena: 1 250,50 zł") == 1250.5


def test_delivery_before_item_price_is_not_selected() -> None:
    text = "Dostawa 10 zł. Cena przedmiotu 1200 zł"
    observations = _price_observations_from_text(text)
    assert [(row.amount, row.kind) for row in observations] == [
        (10.0, "delivery"),
        (1200.0, "item"),
    ]
    assert _price_from_text(text) == 1200.0


def test_currency_and_non_item_price_kinds_are_preserved() -> None:
    json_ld = [{"@type": "Offer", "price": "299", "priceCurrency": "USD"}]
    assert _price_observations_from_json_ld(json_ld)[0].currency == "USD"
    assert _price_observations_from_text("Rata 49 zł miesięcznie")[0].kind == "installment"
    assert _price_observations_from_text("49 zł / mies.")[0].kind == "installment"
    assert _price_observations_from_text("Poprzednia cena 100 zł")[0].kind == "previous"
    assert _price_observations_from_text("Cena od 100 do 200 zł")[0].kind == "range"


def test_visible_and_metadata_price_conflict_is_quarantined() -> None:
    from marketplace_agent.research.extractors import PriceObservation

    observations = [
        PriceObservation(100, "PLN", "item", "meta", "100"),
        PriceObservation(1200, "PLN", "item", "visible_text", "1200 zł"),
    ]
    assert _select_item_price(observations).amount == 1200
    assert _price_integrity_reasons(observations) == [
        "sprzeczne ceny między DOM i metadanymi strony"
    ]


def test_duckduckgo_redirect_is_unwrapped() -> None:
    url = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.olx.pl%2Fd%2Foferta%2Fabc"
    assert unwrap_search_url(url) == "https://www.olx.pl/d/oferta/abc"
