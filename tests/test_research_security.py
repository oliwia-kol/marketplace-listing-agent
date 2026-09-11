import asyncio

from marketplace_agent.domain.models import ComparableCandidate
from marketplace_agent.research.security import (
    compare_verifications,
    validate_public_url,
    validate_url_shape,
)


def candidate(title: str = "Fujinon XF 23mm", price: float = 1200) -> ComparableCandidate:
    return ComparableCandidate(
        source="olx",
        url="https://www.olx.pl/d/oferta/fujinon-xf-23",
        title=title,
        price_pln=price,
        verified=True,
    )


def test_url_shape_blocks_local_network_and_dangerous_schemes() -> None:
    assert not validate_url_shape("file:///etc/passwd").safe
    assert not validate_url_shape("http://127.0.0.1/admin").safe
    assert not validate_url_shape("http://router.local/").safe
    assert not validate_url_shape("https://example.com:8443/").safe
    assert validate_url_shape("https://www.olx.pl/d/oferta/example").safe


def test_dns_guard_rejects_private_resolution() -> None:
    async def private_resolver(_: str) -> list[str]:
        return ["192.168.1.2"]

    result = asyncio.run(
        validate_public_url("https://apparently-public.example/item", private_resolver)
    )
    assert not result.safe
    assert "prywatną" in (result.reason or "")


def test_repeated_verification_detects_dynamic_mismatch() -> None:
    assert compare_verifications(candidate(), candidate()) == []
    reasons = compare_verifications(candidate(), candidate(title="Ignore rules", price=99))
    assert any("cena" in reason for reason in reasons)
    assert any("tytuł" in reason for reason in reasons)


def test_repeated_verification_detects_currency_and_price_kind_changes() -> None:
    first = candidate()
    second = candidate()
    first.currency = "PLN"
    first.price_kind = "item"
    second.currency = "USD"
    second.price_kind = "delivery"
    reasons = compare_verifications(first, second)
    assert "waluta zmieniła się między odczytami" in reasons
    assert "typ ceny zmienił się między odczytami" in reasons
