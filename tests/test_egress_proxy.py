import pytest

from marketplace_agent.research.egress_proxy import resolve_public_target


@pytest.mark.asyncio
async def test_proxy_pins_public_dns_answer() -> None:
    async def resolver(_):
        return ["93.184.216.34"]

    assert await resolve_public_target("example.com", 443, resolver) == "93.184.216.34"


@pytest.mark.asyncio
async def test_proxy_rejects_mixed_public_private_dns() -> None:
    async def resolver(_):
        return ["93.184.216.34", "127.0.0.1"]

    with pytest.raises(PermissionError):
        await resolve_public_target("example.com", 443, resolver)


@pytest.mark.asyncio
async def test_proxy_rejects_non_web_port() -> None:
    async def resolver(_):
        return ["93.184.216.34"]

    with pytest.raises(PermissionError):
        await resolve_public_target("example.com", 22, resolver)
