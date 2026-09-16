from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class WorkflowStatus(StrEnum):
    NEW = "new"
    FACTS_REVIEW = "facts_review"
    PORTALS_REVIEW = "portals_review"
    MARKET_RESEARCH = "market_research"
    PRICE_REVIEW = "price_review"
    COPY_REVIEW = "copy_review"
    FORM_FILLING = "form_filling"
    FORM_NEEDS_USER = "form_needs_user"
    READY_TO_PUBLISH = "ready_to_publish"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    FAILED = "failed"


class FactProposal(BaseModel):
    name: str = Field(
        pattern=(
            r"^(category|brand|model|color|condition|defects|size|material|dimensions|"
            r"completeness|accessories|identifiers|attribute\.[a-z0-9_]+)$"
        ),
        description=(
            "Canonical English key: category, brand, model, color, condition, defects, "
            "size, material, dimensions, completeness, accessories, identifiers, or "
            "attribute.<snake_case>"
        ),
    )
    value: str | int | float | bool | None
    confidence: float = Field(ge=0, le=1)
    source: Literal["image", "user", "model", "derived", "manufacturer"]
    source_ref: str | None = Field(default=None, max_length=128)
    scope: Literal["item", "product_spec"] = "item"
    source_url: HttpUrl | None = None
    source_excerpt: str | None = Field(default=None, max_length=500)
    observed_at: datetime | None = None
    approved: bool = False

    @field_validator("name")
    @classmethod
    def canonical_name(cls, value: str) -> str:
        canonical = {
            "category",
            "brand",
            "model",
            "color",
            "condition",
            "defects",
            "size",
            "material",
            "dimensions",
            "completeness",
            "accessories",
            "identifiers",
        }
        if value.startswith("attribute.") and value.removeprefix("attribute.") in canonical:
            return value.removeprefix("attribute.")
        if value in canonical or value.startswith("attribute."):
            return value
        raise ValueError("Fact name must use a canonical key")

    @model_validator(mode="after")
    def sourced_product_specification(self) -> FactProposal:
        if self.scope == "product_spec" and self.source_url is None:
            raise ValueError("product specifications require source_url")
        return self


class ItemFacts(BaseModel):
    proposals: list[FactProposal] = Field(default_factory=list)

    def approved_dict(
        self, *, scope: Literal["item", "product_spec"] | None = None
    ) -> dict[str, Any]:
        return {
            fact.name: fact.value
            for fact in self.proposals
            if fact.approved and (scope is None or fact.scope == scope)
        }


class ComparableCandidate(BaseModel):
    source: str
    url: HttpUrl
    title: str
    price_pln: float = Field(gt=0)
    currency: Literal["PLN", "EUR", "USD", "UNKNOWN"] = "UNKNOWN"
    price_kind: Literal["item", "delivery", "installment", "previous", "range", "unknown"] = (
        "unknown"
    )
    delivery_pln: float | None = Field(default=None, ge=0)
    condition: str | None = None
    status: Literal["active", "sold", "unknown"] = "unknown"
    verified: bool = False
    comparable: bool = False
    match_score: float = Field(default=0, ge=0, le=1)
    rejection_reason: str | None = None
    integrity_status: Literal["unchecked", "consistent", "suspicious"] = "unchecked"
    integrity_reasons: list[str] = Field(default_factory=list)
    rejection_codes: list[str] = Field(default_factory=list)
    evidence_channels: list[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def total_price_pln(self) -> float:
        return self.price_pln + (self.delivery_pln or 0)


class PricePointCount(BaseModel):
    price_pln: float
    count: int = Field(ge=1)


class PriceRecommendation(BaseModel):
    strategy: Literal["quick", "market", "patient"]
    price_pln: float
    basis: str


class PriceDistribution(BaseModel):
    count: int = 0
    by_source: dict[str, int] = Field(default_factory=dict)
    exact_price_counts: list[PricePointCount] = Field(default_factory=list)
    minimum_pln: float | None = None
    p25_pln: float | None = None
    median_pln: float | None = None
    trimmed_mean_pln: float | None = None
    p75_pln: float | None = None
    maximum_pln: float | None = None


class PriceResearchSummary(BaseModel):
    checked_count: int = 0
    reachable_count: int = 0
    comparable_count: int = 0
    rejected_count: int = 0
    quarantined_count: int = 0
    by_source: dict[str, int] = Field(default_factory=dict)
    exact_price_counts: list[PricePointCount] = Field(default_factory=list)
    active_count: int = 0
    sold_count: int = 0
    active_distribution: PriceDistribution = Field(default_factory=PriceDistribution)
    sold_distribution: PriceDistribution = Field(default_factory=PriceDistribution)
    minimum_pln: float | None = None
    p25_pln: float | None = None
    median_pln: float | None = None
    trimmed_mean_pln: float | None = None
    p75_pln: float | None = None
    maximum_pln: float | None = None
    recommendations: list[PriceRecommendation] = Field(default_factory=list)
    recommendation_basis: Literal["active_asking_prices"] = "active_asking_prices"
    evidence_manifest_path: str | None = None
    confidence: Literal["low", "medium", "high"] = "low"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PortalDraft(BaseModel):
    portal: Literal["olx", "allegro_lokalnie", "vinted"]
    title: str
    description: str
    category: str
    price_pln: float = Field(gt=0)
    condition: str | None = None
    sale_type: Literal["buy_now", "auction", "classified"] | None = None
    location: str | None = None
    delivery: dict[str, str | int | float | bool] = Field(default_factory=dict)
    attributes: dict[str, str | int | float | bool] = Field(default_factory=dict)
    approved: bool = False


class PortalFillResult(BaseModel):
    portal: str
    status: Literal["ready", "needs_user", "failed"]
    form_url: str | None = None
    filled_fields: dict[str, Any] = Field(default_factory=dict)
    differences: dict[str, dict[str, Any]] = Field(default_factory=dict)
    screenshot_path: Path | None = None
    message: str | None = None


class ItemCase(BaseModel):
    item_id: str = Field(default_factory=lambda: uuid4().hex)
    status: WorkflowStatus = WorkflowStatus.NEW
    photo_paths: list[Path] = Field(default_factory=list)
    facts: ItemFacts = Field(default_factory=ItemFacts)
    recommended_portals: list[str] = Field(default_factory=list)
    selected_portals: list[str] = Field(default_factory=list)
    price_summary: PriceResearchSummary | None = None
    selected_price_pln: float | None = None
    portal_drafts: list[PortalDraft] = Field(default_factory=list)
    snapshot_ids: dict[str, str] = Field(default_factory=dict)
    fill_results: list[PortalFillResult] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("selected_portals")
    @classmethod
    def supported_portals(cls, value: list[str]) -> list[str]:
        supported = {"olx", "allegro_lokalnie", "vinted"}
        invalid = set(value) - supported
        if invalid:
            raise ValueError(f"Unsupported portals: {sorted(invalid)}")
        return value
