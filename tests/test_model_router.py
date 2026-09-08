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
