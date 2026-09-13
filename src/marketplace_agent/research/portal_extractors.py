from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

PRICE_PATTERN = re.compile(
    r"(?<!\d)(?P<integer>\d{1,3}(?:[ .]\d{3})*|\d+)"
    r"(?:[,.](?P<decimal>\d{1,2}))?\s*"
    r"(?P<currency>zł|PLN|EUR|USD|€|\$)",
    re.IGNORECASE,
)

SOLD_MARKERS = ("sprzedane", "sprzedany", "przedmiot został sprzedany")
EXPIRED_MARKERS = ("ogłoszenie nieaktualne", "oferta zakończona")


@dataclass(frozen=True, slots=True)
class PortalListingFields:
    """Small trusted projection of the portal DOM used as pricing evidence."""

    title: str
    amount: float
    currency: str
    status: str
    primary_channel: str
    previous_amount: float | None = None


def _normalize_currency(value: str | None) -> str:
    normalized = str(value or "").strip().upper()
    return {"ZŁ": "PLN", "ZL": "PLN", "PLN": "PLN", "€": "EUR", "$": "USD"}.get(
        normalized, normalized if normalized in {"EUR", "USD"} else "UNKNOWN"
    )


def _parse_visible_price(text: str) -> tuple[float, str] | None:
    match = PRICE_PATTERN.search(text)
    if match is None:
        return None
    whole = match.group("integer").replace(" ", "").replace(".", "")
    amount = float(f"{whole}.{match.group('decimal') or '0'}")
    return amount, _normalize_currency(match.group("currency"))


def _status(text: str) -> str:
    lowered = text.casefold()
    if any(marker in lowered for marker in SOLD_MARKERS):
        return "sold"
    if any(marker in lowered for marker in EXPIRED_MARKERS):
        return "unknown"
    return "active"


def _listing_status(soup: BeautifulSoup) -> str:
    """Ignore status words carried by recommendation cards below the listing."""
    for selector in (
        '[data-testid="recommendations"]',
        '[aria-label="Polecane oferty"]',
    ):
        for node in soup.select(selector):
            node.decompose()
    return _status(soup.get_text(" ", strip=True))


def _parse_olx(soup: BeautifulSoup) -> PortalListingFields | None:
    title_node = soup.select_one('[data-testid="offer_title"]')
    price_node = soup.select_one('[data-testid="ad-price-container"]')
    parsed = _parse_visible_price(price_node.get_text(" ", strip=True)) if price_node else None
    if title_node is None or parsed is None:
        return None
    amount, currency = parsed
    return PortalListingFields(
        title=title_node.get_text(" ", strip=True),
        amount=amount,
        currency=currency,
        status=_listing_status(soup),
        primary_channel="olx_primary_dom",
    )


def _parse_allegro_lokalnie(soup: BeautifulSoup) -> PortalListingFields | None:
    overview = soup.select_one('[data-testid="offer-overview-card"]')
    title_node = overview.select_one("h1") if overview else soup.select_one("h1")
    price_node = soup.select_one('meta[itemprop="price"]')
    currency_node = soup.select_one('meta[itemprop="priceCurrency"]')
    if title_node is None or price_node is None:
        return None
    try:
        amount = float(str(price_node.get("content", "")).replace(" ", "").replace(",", "."))
    except ValueError:
        return None
    old_price_node = soup.select_one('[data-testid="old-price-listing"]')
    previous = (
        _parse_visible_price(old_price_node.get_text(" ", strip=True)) if old_price_node else None
    )
    return PortalListingFields(
        title=title_node.get_text(" ", strip=True),
        amount=amount,
        currency=_normalize_currency(
            str(currency_node.get("content", "")) if currency_node else None
        ),
        status=_listing_status(soup),
        primary_channel="allegro_lokalnie_primary_meta",
        previous_amount=previous[0] if previous else None,
    )


def parse_portal_listing(source: str, html: str) -> PortalListingFields | None:
    """Parse only source-specific primary-offer regions, never recommendation cards."""
    soup = BeautifulSoup(html, "html.parser")
    if source == "olx":
        return _parse_olx(soup)
    if source == "allegro_lokalnie":
        return _parse_allegro_lokalnie(soup)
    return None
