from __future__ import annotations

from dataclasses import dataclass

from marketplace_agent.browser.service import BrowserFillService
from marketplace_agent.domain.catalog import CatalogRepository
from marketplace_agent.models.router import ModelRouter
from marketplace_agent.research.service import MarketResearchService


@dataclass(slots=True)
class WorkflowDependencies:
    router: ModelRouter
    research: MarketResearchService
    browser_fill: BrowserFillService
    catalog: CatalogRepository
