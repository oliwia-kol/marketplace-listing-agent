from __future__ import annotations

import asyncio
from collections.abc import Iterable
from urllib.parse import quote_plus, urljoin, urlparse, urlunparse

from playwright.async_api import BrowserContext

from marketplace_agent.research.config import SourceConfig
from marketplace_agent.research.extractors import unwrap_search_url


def host_matches_domain(host: str | None, expected_domain: str) -> bool:
    if not host:
        return False
    normalized = host.rstrip(".").casefold()
    expected = expected_domain.rstrip(".").casefold()
    return normalized == expected or normalized.endswith(f".{expected}")


def canonicalize_listing_url(url: str) -> str:
    """Remove fragments and tracking query data before deduplication."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").rstrip(".").casefold().removeprefix("www.")
    port = f":{parsed.port}" if parsed.port not in {None, 80, 443} else ""
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.casefold(), f"{host}{port}", path, "", "", ""))


class SearchSource:
    def __init__(self, config: SourceConfig, context: BrowserContext) -> None:
        self.config = config
        self.context = context

    async def discover(self, queries: Iterable[str], limit: int) -> list[str]:
        found: list[str] = []
        page = await self.context.new_page()
        try:
            for query in queries:
                if len(found) >= limit:
                    break
                url = self.config.search_url.format(query=quote_plus(query))
                await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                await page.wait_for_timeout(750)
                for href in await page.locator("a[href]").evaluate_all(
                    "elements => elements.map(element => element.href)"
                ):
                    candidate = unwrap_search_url(urljoin(url, href))
                    parsed = urlparse(candidate)
                    if not parsed.scheme.startswith("http"):
                        continue
                    if self.config.id == "web_discovery" and host_matches_domain(
                        parsed.hostname, self.config.domain
                    ):
                        continue
                    if self.config.id != "web_discovery":
                        if not host_matches_domain(parsed.hostname, self.config.domain):
                            continue
                        if (
                            self.config.listing_path_contains
                            and self.config.listing_path_contains not in parsed.path
                        ):
                            continue
                    if candidate not in found:
                        found.append(candidate)
                        if len(found) >= limit:
                            break
                await asyncio.sleep(0.25)
        finally:
            await page.close()
        return found
