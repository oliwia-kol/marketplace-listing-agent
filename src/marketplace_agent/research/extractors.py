from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from playwright.async_api import Page

PRICE_PATTERN = re.compile(
    r"(?<!\d)(?P<integer>\d{1,3}(?:[ .]\d{3})*|\d+)"
    r"(?:[,.](?P<decimal>\d{1,2}))?\s*"
    r"(?P<currency>zł|PLN|EUR|USD|€|\$)",
    re.IGNORECASE,
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
    currency: str = "UNKNOWN"
    price_kind: str = "unknown"
    blocked: bool = False
    expired: bool = False
    evidence_channels: tuple[str, ...] = ()
    integrity_reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PriceObservation:
    amount: float
    currency: str
    kind: str
    channel: str
    raw: str


def _normalize_currency(value: Any) -> str:
    normalized = str(value or "").strip().upper()
    return {
        "ZŁ": "PLN",
        "ZL": "PLN",
        "PLN": "PLN",
        "€": "EUR",
        "EUR": "EUR",
        "$": "USD",
        "USD": "USD",
    }.get(normalized, "UNKNOWN")


def _parse_amount(integer: str, decimal: str | None = None) -> float:
    whole = integer.replace(" ", "").replace(".", "")
    return float(f"{whole}.{decimal or '0'}")


def _price_kind(text: str, match_start: int) -> str:
    boundary = max(text.rfind(".", 0, match_start), text.rfind("\n", 0, match_start))
    next_dot = text.find(".", match_start)
    next_newline = text.find("\n", match_start)
    endings = [position for position in (next_dot, next_newline) if position >= 0]
    end = min(endings) if endings else match_start + 40
    context = text[boundary + 1 : end].casefold()[-120:]
    prefix = text[boundary + 1 : match_start].casefold()[-80:]
    if re.search(r"(?:dostaw|wysył|przesył|transport)", context):
        return "delivery"
    if re.search(r"(?:rata|raty|miesięcz|/\s*mies)", context):
        return "installment"
    if re.search(
        r"(?:poprzednia|stara cena|było|przed obniż|cena początkowa)", context
    ):
        return "previous"
    if re.search(r"\d[\d ,.]*\s*(?:-|\u2013|\u2014|do)\s*$", prefix):
        return "range"
    return "item"


def _price_observations_from_text(text: str) -> list[PriceObservation]:
    observations: list[PriceObservation] = []
    for match in PRICE_PATTERN.finditer(text):
        observations.append(
            PriceObservation(
                amount=_parse_amount(match.group("integer"), match.group("decimal")),
                currency=_normalize_currency(match.group("currency")),
                kind=_price_kind(text, match.start()),
                channel="visible_text",
                raw=match.group(0),
            )
        )
    return observations


def _select_item_price(observations: list[PriceObservation]) -> PriceObservation | None:
    item_observations = [row for row in observations if row.kind == "item"]
    return next(
        (row for row in item_observations if row.channel == "visible_text"),
        item_observations[0] if item_observations else None,
    )


def _price_integrity_reasons(observations: list[PriceObservation]) -> list[str]:
    item_observations = [row for row in observations if row.kind == "item"]
    reasons: list[str] = []
    currencies = {row.currency for row in item_observations if row.currency != "UNKNOWN"}
    if len(currencies) > 1:
        reasons.append("sprzeczne waluty ceny przedmiotu")
    amounts = [row.amount for row in item_observations]
    if len(amounts) > 1 and max(amounts) - min(amounts) > max(1.0, min(amounts) * 0.01):
        reasons.append("sprzeczne ceny między DOM i metadanymi strony")
    return reasons


def _walk_json(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _price_observations_from_json_ld(documents: list[Any]) -> list[PriceObservation]:
    observations: list[PriceObservation] = []
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
                        amount = float(str(raw_price).replace(" ", "").replace(",", "."))
                    except (TypeError, ValueError):
                        continue
                    observations.append(
                        PriceObservation(
                            amount=amount,
                            currency=_normalize_currency(
                                offer.get("priceCurrency") or node.get("priceCurrency")
                            ),
                            kind=(
                                "range"
                                if "price" not in offer and "lowPrice" in offer
                                else "item"
                            ),
                            channel="json_ld",
                            raw=str(raw_price),
                        )
                    )
    return observations


def _price_from_json_ld(documents: list[Any]) -> float | None:
    observations = _price_observations_from_json_ld(documents)
    return observations[0].amount if observations else None


def _price_from_text(text: str) -> float | None:
    observations = _price_observations_from_text(text)
    item = next((row for row in observations if row.kind == "item"), None)
    return item.amount if item else None


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

    meta_currency_locator = page.locator(
        'meta[property="product:price:currency"], meta[itemprop="priceCurrency"], '
        'meta[property="og:price:currency"]'
    ).first
    raw_meta_currency = (
        await meta_currency_locator.get_attribute("content", timeout=1_000)
        if await meta_currency_locator.count()
        else None
    )
    observations = _price_observations_from_json_ld(json_ld_documents)
    visible_observations = _price_observations_from_text(body)
    visible_item = next((row for row in visible_observations if row.kind == "item"), None)
    if visible_item is not None:
        # Related listings below the primary offer can contain unrelated prices.
        observations.append(visible_item)
    if parsed_meta_price is not None:
        observations.insert(
            0,
            PriceObservation(
                amount=parsed_meta_price,
                currency=_normalize_currency(raw_meta_currency),
                kind="item",
                channel="meta",
                raw=str(meta_price),
            ),
        )
    preferred = _select_item_price(observations)
    price = preferred.amount if preferred else None
    integrity_reasons = _price_integrity_reasons(observations)
    sold = any(marker in lowered for marker in SOLD_MARKERS)
    expired = any(marker in lowered for marker in EXPIRED_MARKERS)
    blocked = any(marker in lowered for marker in CAPTCHA_MARKERS)
    return ExtractedListing(
        title=title,
        price_pln=price,
        currency=preferred.currency if preferred else "UNKNOWN",
        price_kind=preferred.kind if preferred else "unknown",
        condition=None,
        status="sold" if sold else "active" if not expired else "unknown",
        blocked=blocked,
        expired=expired,
        evidence_channels=tuple(
            dict.fromkeys(
                [row.channel for row in observations]
                + (["visible_text"] if visible_observations else [])
            )
        ),
        integrity_reasons=tuple(integrity_reasons),
    )


def unwrap_search_url(url: str) -> str:
    parsed = urlparse(url)
    if "duckduckgo.com" in parsed.netloc:
        target = parse_qs(parsed.query).get("uddg")
        if target:
            return unquote(target[0])
    return url
