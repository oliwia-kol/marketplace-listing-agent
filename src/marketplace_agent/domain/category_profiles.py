from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

SENSITIVE_KEY_PARTS = {"identifier", "serial", "imei", "meid", "udid"}


def redact_sensitive_facts(facts: dict[str, Any]) -> dict[str, Any]:
    """Remove device identifiers from research, copy and form preparation."""
    return {
        key: value
        for key, value in facts.items()
        if not any(part in key.casefold() for part in SENSITIVE_KEY_PARTS)
    }


class CategoryProfile(BaseModel):
    id: str
    label: str
    match_keywords: list[str] = Field(default_factory=list)
    required_groups: list[list[str]] = Field(default_factory=list)
    identity_fields: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    variant_traps: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    privacy_rules: list[str] = Field(default_factory=list)

    def prompt_context(self) -> dict[str, Any]:
        return self.model_dump(exclude={"match_keywords", "required_groups"})

    def research_facts(self, facts: dict[str, Any]) -> dict[str, Any]:
        """Remove secrets before a model can copy them into a web query."""
        return redact_sensitive_facts(facts)


class CategoryProfileCatalog(BaseModel):
    profiles: list[CategoryProfile]

    @classmethod
    def from_yaml(cls, path: Path) -> CategoryProfileCatalog:
        return cls.model_validate(yaml.safe_load(path.read_text()))

    def match(self, facts: dict[str, Any]) -> CategoryProfile | None:
        haystack = " ".join(str(value) for value in facts.values()).casefold()
        ranked = [
            (
                sum(keyword.casefold() in haystack for keyword in profile.match_keywords),
                # Profiles passing all required groups are valid even when their
                # ranking phrases are not contiguous in user text.
                profile,
            )
            for profile in self.profiles
            if all(
                any(keyword.casefold() in haystack for keyword in group)
                for group in profile.required_groups
            )
        ]
        score, profile = max(ranked, key=lambda row: row[0], default=(0, None))
        return profile if profile is not None and (score > 0 or profile.required_groups) else None
