from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

OutputT = TypeVar("OutputT", bound=BaseModel)


class StructuredModelResponse[OutputT](BaseModel):
    output: OutputT
    model: str
    total_duration_seconds: float = 0
    load_duration_seconds: float = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ModelProvider(ABC):
    @abstractmethod
    async def structured(
        self,
        *,
        model: str,
        system: str,
        prompt: str,
        output_schema: type[OutputT],
        images: list[Path] | None = None,
        context_tokens: int = 8192,
        think: bool | str = False,
        keep_alive: int | str = 0,
        temperature: float = 0.0,
        top_p: float | None = None,
        top_k: int | None = None,
        seed: int | None = None,
    ) -> StructuredModelResponse[OutputT]:
        raise NotImplementedError

    @abstractmethod
    async def unload(self, model: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def available_models(self) -> list[str]:
        raise NotImplementedError
