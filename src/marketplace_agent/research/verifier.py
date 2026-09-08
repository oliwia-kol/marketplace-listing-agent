from __future__ import annotations

from urllib.parse import urlparse

from playwright.async_api import BrowserContext
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from marketplace_agent.domain.models import ComparableCandidate
from marketplace_agent.research.extractors import extract_listing
from marketplace_agent.research.security import validate_public_url


class LinkVerifier:
    """Verifies the page and extracted evidence, not just the HTTP status."""

    def __init__(self, context: BrowserContext) -> None:
        self.context = context

    async def verify(self, source: str, url: str) -> ComparableCandidate | None:
        initial_safety = await validate_public_url(url)
        if not initial_safety.safe:
            return None
        page = await self.context.new_page()
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            if response is None or response.status >= 400:
                return None
            extracted = await extract_listing(page)
            if extracted.blocked or extracted.expired or extracted.price_pln is None:
                return None
            final_domain = urlparse(page.url).netloc.removeprefix("www.")
            if not final_domain:
                return None
            final_safety = await validate_public_url(page.url)
            if not final_safety.safe:
                return None
            return ComparableCandidate(
                source=source,
                url=page.url,
                title=extracted.title,
                price_pln=extracted.price_pln,
                condition=extracted.condition,
                status=extracted.status,
                verified=True,
                integrity_status=("suspicious" if extracted.integrity_reasons else "unchecked"),
                integrity_reasons=list(extracted.integrity_reasons),
                evidence_channels=list(extracted.evidence_channels),
            )
        except PlaywrightTimeoutError:
            return None
        finally:
            await page.close()
