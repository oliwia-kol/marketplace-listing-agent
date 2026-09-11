from __future__ import annotations

from collections import Counter
from statistics import fmean, median

from marketplace_agent.domain.models import (
    ComparableCandidate,
    PricePointCount,
    PriceRecommendation,
    PriceResearchSummary,
)


def pricing_rejection_codes(candidate: ComparableCandidate) -> list[str]:
    """Return deterministic reasons why evidence cannot influence price statistics."""
    codes: list[str] = []
    if not candidate.verified:
        codes.append("NOT_VERIFIED")
    if not candidate.comparable:
        codes.append("NOT_COMPARABLE")
    if candidate.integrity_status == "unchecked":
        codes.append("INTEGRITY_UNCHECKED")
    elif candidate.integrity_status == "suspicious":
        codes.append("INTEGRITY_SUSPICIOUS")
    if candidate.currency != "PLN":
        codes.append("CURRENCY_NOT_PLN")
    if candidate.price_kind != "item":
        codes.append("PRICE_NOT_ITEM")
    if candidate.status not in {"active", "sold"}:
        codes.append("STATUS_UNKNOWN")
    return codes


def is_pricing_eligible(candidate: ComparableCandidate) -> bool:
    return not pricing_rejection_codes(candidate)


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        raise ValueError("Cannot calculate percentile of an empty sample")
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _trimmed_mean(values: list[float], proportion: float = 0.1) -> float:
    ordered = sorted(values)
    trim = int(len(ordered) * proportion)
    trimmed = ordered[trim : len(ordered) - trim] if trim else ordered
    return fmean(trimmed)


def _round_market_price(value: float) -> float:
    step = 1 if value < 50 else 5 if value < 500 else 10
    return float(round(value / step) * step)


def summarize_prices(
    candidates: list[ComparableCandidate],
    *,
    checked_count: int | None = None,
    minimum_comparables: int = 1,
) -> PriceResearchSummary:
    for candidate in candidates:
        candidate.rejection_codes = pricing_rejection_codes(candidate)
    accepted = [candidate for candidate in candidates if is_pricing_eligible(candidate)]
    reachable = [candidate for candidate in candidates if candidate.verified]
    prices = sorted(candidate.price_pln for candidate in accepted)
    source_counts = Counter(candidate.source for candidate in accepted)
    exact_counts = Counter(prices)

    summary = PriceResearchSummary(
        checked_count=checked_count if checked_count is not None else len(candidates),
        reachable_count=len(reachable),
        comparable_count=len(accepted),
        rejected_count=max(0, len(reachable) - len(accepted)),
        quarantined_count=sum(
            candidate.integrity_status == "suspicious" for candidate in reachable
        ),
        by_source=dict(sorted(source_counts.items())),
        exact_price_counts=[
            PricePointCount(price_pln=price, count=count)
            for price, count in sorted(exact_counts.items())
        ],
        active_count=sum(candidate.status == "active" for candidate in accepted),
        sold_count=sum(candidate.status == "sold" for candidate in accepted),
    )
    if not prices:
        return summary

    p25 = _percentile(prices, 0.25)
    p75 = _percentile(prices, 0.75)
    med = float(median(prices))
    summary.minimum_pln = prices[0]
    summary.p25_pln = p25
    summary.median_pln = med
    summary.trimmed_mean_pln = _trimmed_mean(prices)
    summary.p75_pln = p75
    summary.maximum_pln = prices[-1]
    source_diversity = len(source_counts)
    summary.confidence = (
        "high"
        if len(prices) >= 15 and source_diversity >= 2
        else "medium"
        if len(prices) >= 8
        else "low"
    )
    if len(prices) >= minimum_comparables:
        summary.recommendations = [
            PriceRecommendation(strategy="quick", price_pln=_round_market_price(p25), basis="P25"),
            PriceRecommendation(
                strategy="market", price_pln=_round_market_price(med), basis="median"
            ),
            PriceRecommendation(
                strategy="patient", price_pln=_round_market_price(p75), basis="P75"
            ),
        ]
    return summary
