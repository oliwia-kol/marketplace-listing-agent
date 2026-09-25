from __future__ import annotations

from typing import Any, Literal

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


class CopyClaim(BaseModel):
    key: str
    value: str
    scope: Literal["item", "product_spec"]
    required: bool = True
    source_url: str | None = None
    source_excerpt: str | None = None


class CopyBrief(BaseModel):
    claims: list[CopyClaim]
    portals: list[Literal["olx", "allegro_lokalnie", "vinted"]]
    style: Literal["natural_concrete"] = "natural_concrete"
    preferences: list[dict[str, Any]] = Field(default_factory=list)
    prohibited_claim_types: list[str] = Field(default_factory=list)


class CopyTextDraft(BaseModel):
    portal: Literal["olx", "allegro_lokalnie", "vinted"]
    title: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=10, max_length=4000)


class CopyTextOutput(BaseModel):
    drafts: list[CopyTextDraft]


class CopyClaimAssessment(BaseModel):
    text: str
    verdict: Literal["supported", "contradicted", "unsupported", "uncertain"]
    evidence_keys: list[str] = Field(default_factory=list)
    severity: Literal["info", "warning", "critical"] = "warning"


class CopyAuditItem(BaseModel):
    portal: Literal["olx", "allegro_lokalnie", "vinted"]
    safe: bool
    unsupported_claims: list[str] = Field(default_factory=list)
    claims: list[CopyClaimAssessment] = Field(default_factory=list)
    missing_required_keys: list[str] = Field(default_factory=list)


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
