from __future__ import annotations

from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright


class BrowserSessionManager:
    """Owns an isolated research browser and a visible persistent sales browser."""

    def __init__(
        self,
        profile_dir: Path,
        *,
        headless: bool = False,
        research_proxy_url: str | None = None,
    ) -> None:
        self.profile_dir = profile_dir
        self.headless = headless
        self.research_proxy_url = research_proxy_url
        self._playwright: Playwright | None = None
        self._research_browser: Browser | None = None
        self._sales_context: BrowserContext | None = None

    async def start(self) -> None:
        if self._playwright is None:
            self._playwright = await async_playwright().start()

    async def research_context(self) -> BrowserContext:
        if not self.research_proxy_url:
            raise RuntimeError("research proxy is required but not configured")
        await self.start()
        assert self._playwright is not None
        if self._research_browser is None:
            self._research_browser = await self._playwright.chromium.launch(
                channel="chrome",
                headless=self.headless,
                proxy={"server": self.research_proxy_url},
            )
        return await self._research_browser.new_context(locale="pl-PL", timezone_id="Europe/Warsaw")

    async def sales_context(self) -> BrowserContext:
        await self.start()
        assert self._playwright is not None
        if self._sales_context is None:
            self.profile_dir.mkdir(parents=True, exist_ok=True)
            self._sales_context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=self.profile_dir,
                channel="chrome",
                headless=False,
                locale="pl-PL",
                timezone_id="Europe/Warsaw",
                viewport={"width": 1440, "height": 1000},
            )
        return self._sales_context

    async def close(self) -> None:
        if self._sales_context is not None:
            await self._sales_context.close()
        if self._research_browser is not None:
            await self._research_browser.close()
        if self._playwright is not None:
            await self._playwright.stop()
        self._sales_context = None
        self._research_browser = None
        self._playwright = None
