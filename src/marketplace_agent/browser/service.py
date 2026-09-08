from __future__ import annotations

from pathlib import Path

from marketplace_agent.browser.forms import PortalFormFiller
from marketplace_agent.browser.session import BrowserSessionManager
from marketplace_agent.domain.models import PortalDraft, PortalFillResult
from marketplace_agent.models.router import ModelRouter


class BrowserFillService:
    def __init__(
        self, sessions: BrowserSessionManager, router: ModelRouter, data_dir: Path
    ) -> None:
        self.sessions = sessions
        self.router = router
        self.data_dir = data_dir

    async def fill_all(
        self,
        item_id: str,
        drafts: list[PortalDraft],
        photo_paths: list[Path],
    ) -> list[PortalFillResult]:
        context = await self.sessions.sales_context()
        filler = PortalFormFiller(
            context, self.router, self.data_dir / "items" / item_id / "evidence"
        )
        results: list[PortalFillResult] = []
        for (
            draft
        ) in drafts:  # intentionally sequential: predictable state and lower resource pressure
            results.append(await filler.fill(draft, photo_paths))
        return results
