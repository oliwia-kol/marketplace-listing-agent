import pytest

from marketplace_agent.channels.telegram import parse_field_updates, render_interrupt


def test_price_message_distinguishes_active_and_sold_evidence() -> None:
    message = render_interrupt(
        {
            "kind": "price",
            "summary": {
                "reachable_count": 4,
                "comparable_count": 3,
                "quarantined_count": 1,
                "active_count": 2,
                "sold_count": 1,
                "exact_price_counts": [],
                "active_distribution": {"exact_price_counts": [{"price_pln": 1000, "count": 2}]},
                "recommendations": [{"strategy": "market", "price_pln": 1000, "basis": "active"}],
            },
        }
    )
    assert "Aktywne ceny ofertowe: 2; sprzedane: 1" in message
    assert "Rozkład aktywnych ofert: 2 x 1000 zł" in message


def test_missing_fields_accept_friendly_key_value_pairs() -> None:
    assert parse_field_updates("material=wełna; size=M") == {
        "material": "wełna",
        "size": "M",
    }
    assert parse_field_updates('{"color":"granatowy"}') == {"color": "granatowy"}
    with pytest.raises(ValueError):
        parse_field_updates("sama wartość bez nazwy pola")


def test_portal_prompt_mentions_only_enabled_execution_portals() -> None:
    message = render_interrupt(
        {
            "kind": "portals",
            "recommended": ["olx", "allegro_lokalnie"],
            "reasons": {},
        }
    )
    assert "/zmien olx,allegro_lokalnie" in message
    assert "vinted" not in message.casefold()
