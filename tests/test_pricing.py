from marketplace_agent.domain.models import ComparableCandidate
from marketplace_agent.domain.pricing import pricing_rejection_codes, summarize_prices


def candidate(price: float, *, source: str = "olx", accepted: bool = True):
    return ComparableCandidate(
        source=source,
        url=f"https://example.test/{source}/{price}",
        title="Test",
        price_pln=price,
        verified=True,
        comparable=accepted,
        status="active",
        currency="PLN",
        price_kind="item",
        integrity_status="consistent",
    )


def test_price_summary_is_evidence_only() -> None:
    summary = summarize_prices(
        [
            candidate(80),
            candidate(90),
            candidate(100),
            candidate(110),
            candidate(900, accepted=False),
        ]
    )
    assert summary.comparable_count == 4
    assert summary.rejected_count == 1
    assert summary.median_pln == 95
    assert summary.maximum_pln == 110
    assert [row.price_pln for row in summary.recommendations] == [90, 95, 100]


def test_confidence_requires_sample_size_and_source_diversity() -> None:
    rows = [
        candidate(float(value), source="olx" if value % 2 else "vinted") for value in range(1, 16)
    ]
    assert summarize_prices(rows).confidence == "high"


def test_suspicious_candidates_are_counted_but_never_priced() -> None:
    suspicious = candidate(10)
    suspicious.integrity_status = "suspicious"
    summary = summarize_prices([candidate(100), suspicious])
    assert summary.quarantined_count == 1
    assert summary.comparable_count == 1
    assert summary.median_pln == 100
    assert "INTEGRITY_SUSPICIOUS" in suspicious.rejection_codes


def test_unchecked_timeout_candidate_never_affects_statistics() -> None:
    unchecked = candidate(10)
    unchecked.integrity_status = "unchecked"
    summary = summarize_prices([candidate(100), unchecked])
    assert summary.median_pln == 100
    assert pricing_rejection_codes(unchecked) == ["INTEGRITY_UNCHECKED"]


def test_foreign_currency_and_non_item_amount_are_rejected() -> None:
    usd = candidate(299)
    usd.currency = "USD"
    delivery = candidate(10)
    delivery.price_kind = "delivery"
    summary = summarize_prices([candidate(1200), usd, delivery])
    assert summary.comparable_count == 1
    assert summary.median_pln == 1200
    assert "CURRENCY_NOT_PLN" in usd.rejection_codes
    assert "PRICE_NOT_ITEM" in delivery.rejection_codes


def test_minimum_comparables_blocks_recommendations_without_hiding_observations() -> None:
    summary = summarize_prices([candidate(100), candidate(120)], minimum_comparables=3)
    assert summary.comparable_count == 2
    assert summary.median_pln == 110
    assert summary.recommendations == []
