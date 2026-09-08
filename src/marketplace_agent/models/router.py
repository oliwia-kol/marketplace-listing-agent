from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from marketplace_agent.models.base import ModelProvider, OutputT, StructuredModelResponse


class ModelRole(StrEnum):
    VISION_FAST = "vision_fast"
    MARKET_EXPERT = "market_expert"
    POLISH_COPYWRITER = "polish_copywriter"
    GUI_FALLBACK = "gui_fallback"


class RoleConfig(BaseModel):
    model: str
    fallback: str | None = None
    context_tokens: int = Field(default=8192, ge=1024)
    think: bool | str = False
    keep_alive: int | str = 0


class RouterConfig(BaseModel):
    roles: dict[ModelRole, RoleConfig]


class ModelRouter:
    def __init__(self, provider: ModelProvider, config: RouterConfig) -> None:
        self.provider = provider
        self.config = config

    @classmethod
    def from_yaml(cls, provider: ModelProvider, path: Path) -> ModelRouter:
        return cls(provider, RouterConfig.model_validate(yaml.safe_load(path.read_text())))

    async def run(
        self,
        role: ModelRole,
        *,
        system: str,
        prompt: str,
        output_schema: type[OutputT],
        images: list[Path] | None = None,
    ) -> StructuredModelResponse[OutputT]:
        role_config = self.config.roles[role]
        models = [role_config.model] + ([role_config.fallback] if role_config.fallback else [])
        last_error: Exception | None = None
        for model in models:
            if model is None:
                continue
            try:
                return await self.provider.structured(
                    model=model,
                    system=system,
                    prompt=prompt,
                    output_schema=output_schema,
                    images=images,
                    context_tokens=role_config.context_tokens,
                    think=role_config.think,
                    keep_alive=role_config.keep_alive,
                )
            except Exception as error:
                last_error = error
        assert last_error is not None
        raise last_error

    async def validate_installation(self) -> dict[str, Any]:
        installed = set(await self.provider.available_models())
        result: dict[str, Any] = {}
        for role, role_config in self.config.roles.items():
            result[role.value] = {
                "model": role_config.model,
                "installed": role_config.model in installed,
                "fallback": role_config.fallback,
                "fallback_installed": role_config.fallback in installed
                if role_config.fallback
                else None,
            }
        return result
