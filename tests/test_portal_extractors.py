from pathlib import Path

from marketplace_agent.research.portal_extractors import parse_portal_listing

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_olx_parser_reads_only_primary_offer_price() -> None:
    result = parse_portal_listing("olx", fixture("olx_listing.html"))
    assert result is not None
    assert result.title == "Nintendo Switch OLED"
    assert result.amount == 1070
    assert result.currency == "PLN"
    assert result.status == "active"
    assert result.primary_channel == "olx_primary_dom"


def test_allegro_parser_ignores_old_delivery_and_recommendation_prices() -> None:
    result = parse_portal_listing(
        "allegro_lokalnie", fixture("allegro_lokalnie_listing.html")
    )
    assert result is not None
    assert result.title == "Nintendo Switch OLED"
    assert result.amount == 1100
    assert result.currency == "PLN"
    assert result.previous_amount == 1250
    assert result.status == "active"
    assert result.primary_channel == "allegro_lokalnie_primary_meta"


def test_unknown_source_has_no_portal_parser() -> None:
    assert parse_portal_listing("unknown", "<h1>Oferta</h1>") is None
