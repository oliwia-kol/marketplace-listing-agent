import asyncio
from pathlib import Path

import pytest
from pydantic import BaseModel

from marketplace_agent.models.base import StructuredModelResponse
from marketplace_agent.models.router import ModelRole, ModelRouter, RoleConfig, RouterConfig


class Output(BaseModel):
    value: str


class FallbackProvider:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def structured(self, *, model: str, **kwargs):
        self.calls.append(model)
        if model == "primary":
            raise RuntimeError("primary failed")
        return StructuredModelResponse(output=Output(value="ok"), model=model)

    async def unload(self, model: str) -> None:
        return None

    async def available_models(self) -> list[str]:
        return ["fallback"]


@pytest.mark.asyncio
async def test_router_uses_declared_fallback() -> None:
    provider = FallbackProvider()
    config = RouterConfig(
        roles={role: RoleConfig(model="primary", fallback="fallback") for role in ModelRole}
    )
    router = ModelRouter(provider, config)
    response = await router.run(
        ModelRole.MARKET_EXPERT,
        system="test",
        prompt="test",
        output_schema=Output,
        images=[Path("unused")],
    )
    assert response.model == "fallback"
    assert provider.calls == ["primary", "fallback"]


@pytest.mark.asyncio
async def test_router_records_metadata_without_prompt_content() -> None:
    provider = FallbackProvider()
    config = RouterConfig(
        roles={role: RoleConfig(model="primary", fallback="fallback") for role in ModelRole}
    )
    events: list[tuple] = []
    router = ModelRouter(provider, config, lambda *values: events.append(values))
    await router.run(
        ModelRole.MARKET_EXPERT,
        system="tajna instrukcja",
        prompt="sekret użytkownika",
        output_schema=Output,
        run_id="run-1",
        item_id="item-1",
    )

    assert [event[4] for event in events] == ["error", "ok"]
    assert events[-1][5]["fallback_used"] is True
    serialized = repr(events)
    assert "sekret użytkownika" not in serialized
    assert "tajna instrukcja" not in serialized


@pytest.mark.asyncio
async def test_router_times_out_and_records_only_error_metadata() -> None:
    class SlowProvider(FallbackProvider):
        async def structured(self, *, model: str, **kwargs):
            await asyncio.sleep(0.05)
            return StructuredModelResponse(output=Output(value="late"), model=model)

    provider = SlowProvider()
    config = RouterConfig(
        roles={
            role: RoleConfig(model="slow", request_timeout_seconds=0.01)
            for role in ModelRole
        }
    )
    events: list[tuple] = []
    router = ModelRouter(provider, config, lambda *values: events.append(values))

    with pytest.raises(TimeoutError):
        await router.run(
            ModelRole.MARKET_EXPERT,
            system="system",
            prompt="sensitive",
            output_schema=Output,
        )

    assert events[-1][4] == "error"
    assert events[-1][5]["error_type"] == "TimeoutError"
    assert "sensitive" not in repr(events)
