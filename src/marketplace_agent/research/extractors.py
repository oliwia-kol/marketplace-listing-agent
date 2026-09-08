from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from playwright.async_api import Page

PRICE_PATTERN = re.compile(
    r"(?<!\d)(\d{1,3}(?:[ .]\d{3})*|\d+)(?:[,.](\d{1,2}))?\s*(?:zł|PLN)", re.IGNORECASE
)
EXPIRED_MARKERS = (
    "ogłoszenie nieaktualne",
    "oferta zakończona",
    "przedmiot został sprzedany",
    "item is no longer available",
    "404",
)
SOLD_MARKERS = ("sprzedane", "sprzedany", "przedmiot został sprzedany", "sold")
CAPTCHA_MARKERS = ("captcha", "verify you are human", "sprawdź, czy jesteś człowiekiem")


@dataclass(slots=True)
class ExtractedListing:
    title: str
    price_pln: float | None
    condition: str | None
    status: str
    blocked: bool = False
    expired: bool = False
    evidence_channels: tuple[str, ...] = ()
    integrity_reasons: tuple[str, ...] = ()


def _walk_json(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _price_from_json_ld(documents: list[Any]) -> float | None:
    for document in documents:
        for node in _walk_json(document):
            raw_type = node.get("@type")
            types = {raw_type} if isinstance(raw_type, str) else set(raw_type or [])
            if types & {"Offer", "Product"}:
                offers = node.get("offers", node)
                offer_nodes = (
                    [offers]
                    if isinstance(offers, dict)
                    else offers
                    if isinstance(offers, list)
                    else []
                )
                for offer in offer_nodes:
                    if not isinstance(offer, dict):
                        continue
                    raw_price = offer.get("price") or offer.get("lowPrice")
                    try:
                        return float(str(raw_price).replace(" ", "").replace(",", "."))
                    except (TypeError, ValueError):
                        continue
    return None


def _price_from_text(text: str) -> float | None:
    match = PRICE_PATTERN.search(text)
    if not match:
        return None
    integer = match.group(1).replace(" ", "").replace(".", "")
    decimal = match.group(2) or "0"
    return float(f"{integer}.{decimal}")


async def extract_listing(page: Page) -> ExtractedListing:
    title = (await page.title()).strip()
    body = (await page.locator("body").inner_text(timeout=10_000))[:100_000]
    lowered = body.lower()
    json_ld_documents: list[Any] = []
    for raw in await page.locator('script[type="application/ld+json"]').all_text_contents():
        try:
            json_ld_documents.append(json.loads(raw))
        except json.JSONDecodeError:
            continue

    og_title = page.locator('meta[property="og:title"]').first
    if await og_title.count():
        title = (await og_title.get_attribute("content", timeout=1_000) or title).strip()
    else:
        heading = page.locator("h1").first
        if await heading.count():
            title = (await heading.inner_text(timeout=1_000) or title).strip()

    price_selector = (
        'meta[property="product:price:amount"], meta[itemprop="price"], '
        'meta[property="og:price:amount"]'
    )
    meta_locator = page.locator(price_selector).first
    meta_price = (
        await meta_locator.get_attribute("content", timeout=1_000)
        if await meta_locator.count()
        else None
    )
    try:
        parsed_meta_price = float(str(meta_price).replace(",", ".")) if meta_price else None
    except ValueError:
        parsed_meta_price = None

    json_ld_price = _price_from_json_ld(json_ld_documents)
    text_price = _price_from_text(body)
    evidence = {
        "meta": parsed_meta_price,
        "json_ld": json_ld_price,
        "visible_text": text_price,
    }
    price = parsed_meta_price or json_ld_price or text_price
    structured_prices = [
        value for key, value in evidence.items() if key != "visible_text" and value
    ]
    integrity_reasons: list[str] = []
    if len(structured_prices) > 1 and (
        max(structured_prices) - min(structured_prices) > max(1.0, min(structured_prices) * 0.01)
    ):
        integrity_reasons.append("sprzeczne ceny w metadanych strony")
    sold = any(marker in lowered for marker in SOLD_MARKERS)
    expired = any(marker in lowered for marker in EXPIRED_MARKERS)
    blocked = any(marker in lowered for marker in CAPTCHA_MARKERS)
    return ExtractedListing(
        title=title,
        price_pln=price,
        condition=None,
        status="sold" if sold else "active" if not expired else "unknown",
        blocked=blocked,
        expired=expired,
        evidence_channels=tuple(key for key, value in evidence.items() if value is not None),
        integrity_reasons=tuple(integrity_reasons),
    )


def unwrap_search_url(url: str) -> str:
    parsed = urlparse(url)
    if "duckduckgo.com" in parsed.netloc:
        target = parse_qs(parsed.query).get("uddg")
        if target:
            return unquote(target[0])
    return url
