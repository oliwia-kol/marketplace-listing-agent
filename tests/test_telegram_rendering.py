from marketplace_agent.channels.telegram import render_interrupt


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
                "active_distribution": {
                    "exact_price_counts": [{"price_pln": 1000, "count": 2}]
                },
                "recommendations": [
                    {"strategy": "market", "price_pln": 1000, "basis": "active"}
                ],
            },
        }
    )
    assert "Aktywne ceny ofertowe: 2; sprzedane: 1" in message
    assert "Rozkład aktywnych ofert: 2 x 1000 zł" in message
