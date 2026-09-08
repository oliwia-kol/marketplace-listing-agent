from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from marketplace_agent.domain.models import FactProposal, PortalDraft


class FactExtractionOutput(BaseModel):
    facts: list[FactProposal]
    missing_questions: list[str] = Field(default_factory=list)


class PortalRecommendationOutput(BaseModel):
    portals: list[Literal["olx", "allegro_lokalnie", "vinted"]]
    reasons: dict[str, str]


class SearchPlanOutput(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=8)
    product_identity: str
    must_match: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


class ComparableDecision(BaseModel):
    comparable: bool
    score: float = Field(ge=0, le=1)
    reason: str


class ComparableAuditItem(BaseModel):
    index: int
    comparable: bool
    score: float = Field(ge=0, le=1)
    reason: str


class ComparableAuditOutput(BaseModel):
    decisions: list[ComparableAuditItem]


class CopyDraftOutput(BaseModel):
    drafts: list[PortalDraft]


class CopyAuditItem(BaseModel):
    portal: Literal["olx", "allegro_lokalnie", "vinted"]
    safe: bool
    unsupported_claims: list[str] = Field(default_factory=list)


class CopyAuditOutput(BaseModel):
    decisions: list[CopyAuditItem]


class FormAction(BaseModel):
    action: Literal["fill", "click", "select", "check", "upload"]
    target: str
    value: str | bool | None = None
    confidence: float = Field(ge=0, le=1)


class FormPlanOutput(BaseModel):
    actions: list[FormAction]
    explanation: str
