from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path
from typing import Any

import ollama
from pydantic import BaseModel

from marketplace_agent.models.base import OutputT, StructuredModelResponse


class OllamaModelProvider:
    """Ollama adapter with schema validation and explicit model unloading."""

    def __init__(self, host: str = "http://127.0.0.1:11434") -> None:
        self.client = ollama.AsyncClient(host=host)
        self._lock = asyncio.Lock()

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
    ) -> StructuredModelResponse[OutputT]:
        image_payload = [base64.b64encode(path.read_bytes()).decode() for path in images or []]
        message: dict[str, Any] = {"role": "user", "content": prompt}
        if image_payload:
            message["images"] = image_payload

        async with self._lock:  # hard guarantee: this process never runs two models concurrently
            response = await self.client.chat(
                model=model,
                messages=[{"role": "system", "content": system}, message],
                format=output_schema.model_json_schema(),
                stream=False,
                think=think,
                keep_alive=keep_alive,
                options={"num_ctx": context_tokens, "temperature": 0},
            )
        raw = response.message.content
        try:
            parsed = output_schema.model_validate_json(raw)
        except Exception:
            parsed = output_schema.model_validate(json.loads(raw))
        return StructuredModelResponse[OutputT](
            output=parsed,
            model=model,
            total_duration_seconds=(response.total_duration or 0) / 1_000_000_000,
            load_duration_seconds=(response.load_duration or 0) / 1_000_000_000,
            prompt_tokens=response.prompt_eval_count or 0,
            completion_tokens=response.eval_count or 0,
        )

    async def unload(self, model: str) -> None:
        await self.client.chat(model=model, messages=[], keep_alive=0)

    async def available_models(self) -> list[str]:
        response = await self.client.list()
        return [item.model for item in response.models]


class StaticModelProvider:
    """Deterministic provider used by tests and course exercises."""

    def __init__(self, responses: dict[type[BaseModel], BaseModel]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def structured(
        self, *, output_schema: type[OutputT], **kwargs: Any
    ) -> StructuredModelResponse[OutputT]:
        self.calls.append({"output_schema": output_schema.__name__, **kwargs})
        output = self.responses[output_schema]
        return StructuredModelResponse(output=output, model=str(kwargs.get("model", "static")))

    async def unload(self, model: str) -> None:
        return None

    async def available_models(self) -> list[str]:
        return ["static"]
