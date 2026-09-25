from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import urlparse

from marketplace_agent.domain.models import ComparableCandidate


@dataclass(frozen=True, slots=True)
class UrlSafetyDecision:
    safe: bool
    reason: str | None = None


def validate_url_shape(url: str) -> UrlSafetyDecision:
    """Reject schemes and hosts that could turn research into an SSRF primitive."""
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError:
        return UrlSafetyDecision(False, "nieprawidłowy port")
    if parsed.scheme not in {"http", "https"}:
        return UrlSafetyDecision(False, "dozwolone są tylko adresy HTTP(S)")
    if not parsed.hostname:
        return UrlSafetyDecision(False, "brak hosta")
    if parsed.username or parsed.password:
        return UrlSafetyDecision(False, "adres zawiera dane logowania")
    if port not in {None, 80, 443}:
        return UrlSafetyDecision(False, "niedozwolony port")
    host = parsed.hostname.rstrip(".").casefold()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        return UrlSafetyDecision(False, "host lokalny")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return UrlSafetyDecision(True)
    return (
        UrlSafetyDecision(True)
        if address.is_global
        else UrlSafetyDecision(False, "adres IP nie jest publiczny")
    )


async def validate_public_url(
    url: str,
    resolver: Callable[[str], Awaitable[list[str]]] | None = None,
) -> UrlSafetyDecision:
    shape = validate_url_shape(url)
    if not shape.safe:
        return shape
    host = urlparse(url).hostname
    assert host is not None

    async def default_resolver(value: str) -> list[str]:
        loop = asyncio.get_running_loop()
        rows = await loop.getaddrinfo(value, None, type=socket.SOCK_STREAM)
        return list({row[4][0] for row in rows})

    try:
        addresses = await (resolver or default_resolver)(host)
    except (OSError, socket.gaierror):
        return UrlSafetyDecision(False, "nie udało się bezpiecznie rozwiązać DNS")
    if not addresses:
        return UrlSafetyDecision(False, "DNS nie zwrócił adresu")
    for raw in addresses:
        try:
            address = ipaddress.ip_address(raw)
        except ValueError:
            return UrlSafetyDecision(False, "DNS zwrócił nieprawidłowy adres")
        if not address.is_global:
            return UrlSafetyDecision(False, "DNS wskazuje sieć prywatną lub specjalną")
    return UrlSafetyDecision(True)


def compare_verifications(
    first: ComparableCandidate,
    second: ComparableCandidate,
) -> list[str]:
    reasons: list[str] = []
    first_url = urlparse(str(first.url))
    second_url = urlparse(str(second.url))
    if (first_url.hostname, first_url.path.rstrip("/")) != (
        second_url.hostname,
        second_url.path.rstrip("/"),
    ):
        reasons.append("adres docelowy zmienił się między odczytami")
    if abs(first.price_pln - second.price_pln) > max(1.0, first.price_pln * 0.01):
        reasons.append("cena zmieniła się między odczytami")
    if first.currency != second.currency:
        reasons.append("waluta zmieniła się między odczytami")
    if first.price_kind != second.price_kind:
        reasons.append("typ ceny zmienił się między odczytami")
    first_tokens = set(first.title.casefold().split())
    second_tokens = set(second.title.casefold().split())
    overlap = len(first_tokens & second_tokens) / max(1, len(first_tokens | second_tokens))
    if overlap < 0.6:
        reasons.append("tytuł znacząco zmienił się między odczytami")
    if first.status != second.status:
        reasons.append("status oferty zmienił się między odczytami")
    return reasons
