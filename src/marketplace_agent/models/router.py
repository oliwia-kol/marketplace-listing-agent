from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

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
    request_timeout_seconds: float = Field(default=180.0, ge=0.01)
    temperature: float = Field(default=0.0, ge=0, le=2)
    top_p: float | None = Field(default=None, gt=0, le=1)
    top_k: int | None = Field(default=None, ge=1)
    seed: int | None = None


class RouterConfig(BaseModel):
    roles: dict[ModelRole, RoleConfig]


class ModelRouter:
    def __init__(
        self,
        provider: ModelProvider,
        config: RouterConfig,
        event_sink: Callable[[str, str | None, str, str, str, dict[str, Any]], None] | None = None,
    ) -> None:
        self.provider = provider
        self.config = config
        self.event_sink = event_sink

    @classmethod
    def from_yaml(
        cls,
        provider: ModelProvider,
        path: Path,
        event_sink: Callable[[str, str | None, str, str, str, dict[str, Any]], None] | None = None,
    ) -> ModelRouter:
        return cls(
            provider,
            RouterConfig.model_validate(yaml.safe_load(path.read_text())),
            event_sink,
        )

    async def run(
        self,
        role: ModelRole,
        *,
        system: str,
        prompt: str,
        output_schema: type[OutputT],
        images: list[Path] | None = None,
        run_id: str | None = None,
        item_id: str | None = None,
    ) -> StructuredModelResponse[OutputT]:
        role_config = self.config.roles[role]
        models = [role_config.model] + ([role_config.fallback] if role_config.fallback else [])
        last_error: Exception | None = None
        effective_run_id = run_id or uuid4().hex
        system_hash = hashlib.sha256(system.encode()).hexdigest()[:16]
        for attempt, model in enumerate(models, 1):
            if model is None:
                continue
            try:
                async with asyncio.timeout(role_config.request_timeout_seconds):
                    response = await self.provider.structured(
                        model=model,
                        system=system,
                        prompt=prompt,
                        output_schema=output_schema,
                        images=images,
                        context_tokens=role_config.context_tokens,
                        think=role_config.think,
                        keep_alive=role_config.keep_alive,
                        temperature=role_config.temperature,
                        top_p=role_config.top_p,
                        top_k=role_config.top_k,
                        seed=role_config.seed,
                    )
                self._record(
                    effective_run_id,
                    item_id,
                    role,
                    "ok",
                    {
                        "model": response.model,
                        "attempt": attempt,
                        "fallback_used": attempt > 1,
                        "system_hash": system_hash,
                        "schema": output_schema.__name__,
                        "duration_seconds": response.total_duration_seconds,
                        "load_seconds": response.load_duration_seconds,
                        "prompt_tokens": response.prompt_tokens,
                        "completion_tokens": response.completion_tokens,
                    },
                )
                return response
            except Exception as error:
                last_error = error
                self._record(
                    effective_run_id,
                    item_id,
                    role,
                    "error",
                    {
                        "model": model,
                        "attempt": attempt,
                        "fallback_used": attempt > 1,
                        "system_hash": system_hash,
                        "schema": output_schema.__name__,
                        "error_type": type(error).__name__,
                    },
                )
        assert last_error is not None
        raise last_error

    def _record(
        self,
        run_id: str,
        item_id: str | None,
        role: ModelRole,
        status: str,
        payload: dict[str, Any],
    ) -> None:
        if self.event_sink is not None:
            self.event_sink(run_id, item_id, "model", role.value, status, payload)

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
