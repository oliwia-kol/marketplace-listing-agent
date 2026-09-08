from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ResearchLimits(BaseModel):
    target_comparables: int = Field(default=25, ge=1)
    minimum_comparables: int = Field(default=8, ge=1)
    timeout_seconds: int = Field(default=600, ge=10)
    max_candidate_urls: int = Field(default=60, ge=1)
    max_parallel_domains: int = Field(default=3, ge=1)
    per_domain_concurrency: int = Field(default=1, ge=1)
    request_delay_seconds: float = Field(default=2, ge=0)


class SourceConfig(BaseModel):
    id: str
    domain: str
    search_url: str
    listing_path_contains: str | None = None
    enabled: bool = True


class ResearchConfig(BaseModel):
    research: ResearchLimits
    sources: list[SourceConfig]

    @classmethod
    def from_yaml(cls, path: Path) -> ResearchConfig:
        return cls.model_validate(yaml.safe_load(path.read_text()))
