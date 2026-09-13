from __future__ import annotations

from contextlib import AsyncExitStack
from typing import Any

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from marketplace_agent.browser.service import BrowserFillService
from marketplace_agent.browser.session import BrowserSessionManager
from marketplace_agent.domain.catalog import CatalogRepository
from marketplace_agent.domain.category_profiles import CategoryProfileCatalog
from marketplace_agent.models.ollama_provider import OllamaModelProvider
from marketplace_agent.models.router import ModelRouter
from marketplace_agent.research.config import ResearchConfig
from marketplace_agent.research.service import MarketResearchService
from marketplace_agent.settings import Settings
from marketplace_agent.workflow.dependencies import WorkflowDependencies
from marketplace_agent.workflow.graph import build_graph


class ApplicationRuntime:
    """Own long-lived resources and close them in reverse order."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.stack = AsyncExitStack()
        self.sessions: BrowserSessionManager | None = None
        self.graph: Any = None
        self.router: ModelRouter | None = None
        self.catalog: CatalogRepository | None = None

    async def __aenter__(self) -> ApplicationRuntime:
        self.settings.ensure_directories()
        assert self.settings.model_config_path is not None
        assert self.settings.source_config_path is not None
        assert self.settings.category_profile_path is not None
        assert self.settings.data_dir is not None
        self.catalog = CatalogRepository(self.settings.catalog_db)
        self.catalog.setup()
        provider = OllamaModelProvider()
        self.router = ModelRouter.from_yaml(
            provider,
            self.settings.model_config_path,
            event_sink=self.catalog.record_run_event,
        )
        self.sessions = BrowserSessionManager(
            self.settings.chrome_profile_dir, headless=self.settings.headless
        )
        saver = await self.stack.enter_async_context(
            AsyncSqliteSaver.from_conn_string(str(self.settings.checkpoint_db))
        )
        deps = WorkflowDependencies(
            router=self.router,
            research=MarketResearchService(
                self.sessions,
                self.router,
                ResearchConfig.from_yaml(self.settings.source_config_path),
                CategoryProfileCatalog.from_yaml(self.settings.category_profile_path),
                data_dir=self.settings.data_dir,
            ),
            browser_fill=BrowserFillService(self.sessions, self.router, self.settings.data_dir),
            catalog=self.catalog,
        )
        self.graph = build_graph(deps, saver)
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self.sessions is not None:
            await self.sessions.close()
        await self.stack.aclose()
