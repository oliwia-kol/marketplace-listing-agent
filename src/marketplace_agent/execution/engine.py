from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from marketplace_agent.browser.forms import PORTAL_SPECS, PortalFormFiller, detect_page_blocker
from marketplace_agent.browser.session import BrowserSessionManager
from marketplace_agent.domain.catalog import CatalogRepository
from marketplace_agent.domain.models import PortalDraft
from marketplace_agent.models.router import ModelRouter


@dataclass(frozen=True, slots=True)
class PreparationResult:
    status: str
    evidence: dict[str, Any]
    intervention_kind: str | None = None
    instruction: str | None = None


class ExecutionAdapter(Protocol):
    async def prepare(self, snapshot: dict[str, Any]) -> PreparationResult: ...

    async def publish(
        self, snapshot: dict[str, Any], previous_result: dict[str, Any]
    ) -> PreparationResult: ...

    async def reconcile(self, snapshot: dict[str, Any]) -> PreparationResult: ...


class BrowserExecutionAdapter:
    """Load only an immutable snapshot and prepare a portal form."""

    def __init__(
        self,
        sessions: BrowserSessionManager,
        router: ModelRouter,
        data_dir: Path,
        *,
        allow_live_submit: bool = False,
    ) -> None:
        self.sessions = sessions
        self.router = router
        self.data_dir = data_dir
        self.allow_live_submit = allow_live_submit

    def _verified_photo_paths(self, snapshot: dict[str, Any]) -> list[Path] | None:
        payload = snapshot["payload"]
        photo_dir = self.data_dir / "items" / snapshot["item_id"] / "photos"
        paths: list[Path] = []
        for record in sorted(payload["photos"], key=lambda value: value["index"]):
            path = photo_dir / record["file_name"]
            if (
                not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]
            ):
                return None
            paths.append(path)
        return paths

    async def prepare(self, snapshot: dict[str, Any]) -> PreparationResult:
        payload = snapshot["payload"]
        item_id = snapshot["item_id"]
        photo_paths = self._verified_photo_paths(snapshot)
        if photo_paths is None:
            return PreparationResult("failed", {"reason": "photo_snapshot_mismatch"})
        context = await self.sessions.sales_context()
        filler = PortalFormFiller(
            context,
            self.router,
            self.data_dir / "items" / item_id / "evidence",
        )
        result = await filler.fill(PortalDraft.model_validate(payload["draft"]), photo_paths)
        evidence = result.model_dump(mode="json")
        if result.status == "ready":
            return PreparationResult("ready", evidence)
        kind = (
            result.message.removeprefix("intervention:")
            if result.message and result.message.startswith("intervention:")
            else "unknown_field_or_readback"
        )
        instructions = {
            "captcha": "Rozwiąż CAPTCHA w otwartym oknie i wybierz Kontynuuj.",
            "login_required": "Zaloguj się bezpośrednio w otwartym Chrome i wybierz Kontynuuj.",
            "unexpected_fee": (
                "Sprawdź widoczną opłatę. Zadanie nie będzie kontynuowane automatycznie."
            ),
            "unknown_field_or_readback": (
                "Sprawdź pola formularza; automat wykrył brak lub różnicę."
            ),
        }
        return PreparationResult(
            "waiting_user", evidence, intervention_kind=kind, instruction=instructions[kind]
        )

    async def publish(
        self, snapshot: dict[str, Any], previous_result: dict[str, Any]
    ) -> PreparationResult:
        if not self.allow_live_submit:
            return PreparationResult(
                "waiting_user",
                {"reason": "live_submit_disabled"},
                "live_submit_disabled",
                "Włącz publikację dopiero dla kontrolowanego testu zatwierdzonego snapshotu.",
            )
        payload = snapshot["payload"]
        draft = PortalDraft.model_validate(payload["draft"])
        photo_paths = self._verified_photo_paths(snapshot)
        if photo_paths is None:
            return PreparationResult("failed", {"reason": "photo_snapshot_mismatch"})
        context = await self.sessions.sales_context()
        filler = PortalFormFiller(
            context,
            self.router,
            self.data_dir / "items" / snapshot["item_id"] / "evidence",
        )
        page = await filler._page_for_portal(PORTAL_SPECS[draft.portal])
        blocker = await detect_page_blocker(page)
        if blocker:
            return PreparationResult("waiting_user", {"url": page.url}, blocker, blocker)
        # Publication is the final safety boundary. Re-read every expected
        # business field, even if an older preparation result omitted a key.
        expected_fields = {
            key: True for key in (
                "title", "description", "price_pln", "category", "condition",
                "sale_type", "location", "photos"
            )
        }
        differences = await filler._readback(page, draft, expected_fields, photo_paths)
        if differences:
            return PreparationResult(
                "waiting_user",
                {"differences": differences},
                "manual_change_detected",
                "Formularz różni się od snapshotu. Wymagany jest nowy podgląd i zgoda.",
            )
        labels = {
            "olx": ("Dodaj ogłoszenie", "Opublikuj"),
            "allegro_lokalnie": ("Wystaw",),
        }[draft.portal]
        matches = []
        for label in labels:
            button = page.get_by_role("button", name=label, exact=True)
            if await button.count() == 1:
                matches.append(button)
        if len(matches) != 1:
            return PreparationResult(
                "waiting_user",
                {"matching_publish_controls": len(matches)},
                "unknown_publish_control",
                "Nie znaleziono dokładnie jednego dozwolonego przycisku publikacji.",
            )
        try:
            await matches[0].click(timeout=10_000)
            await page.wait_for_load_state("domcontentloaded", timeout=15_000)
        except PlaywrightTimeoutError:
            return PreparationResult("unknown", {"reason": "submit_outcome_unknown"})
        body = (await page.locator("body").inner_text()).casefold()
        if any(marker in body for marker in ("ogłoszenie zostało", "oferta została wystawiona")):
            return PreparationResult("published", {"url": page.url})
        if "moderac" in body:
            return PreparationResult("pending_moderation", {"url": page.url})
        return PreparationResult("unknown", {"url": page.url, "reason": "no_confirmation"})

    async def reconcile(self, snapshot: dict[str, Any]) -> PreparationResult:
        portal = snapshot["portal"]
        context = await self.sessions.sales_context()
        pages = [
            page
            for page in context.pages
            if PORTAL_SPECS[portal].create_url.split("/")[2] in page.url
        ]
        if not pages:
            return PreparationResult("unknown", {"reason": "portal_page_not_open"})
        page = pages[-1]
        body = (await page.locator("body").inner_text()).casefold()
        if any(marker in body for marker in ("ogłoszenie zostało", "oferta została wystawiona")):
            return PreparationResult("published", {"url": page.url, "reconciled": True})
        if "moderac" in body:
            return PreparationResult("pending_moderation", {"url": page.url, "reconciled": True})
        return PreparationResult("unknown", {"url": page.url, "reason": "not_confirmed"})


class ExecutionEngine:
    def __init__(
        self,
        catalog: CatalogRepository,
        adapter: ExecutionAdapter,
        worker_id: str,
    ) -> None:
        self.catalog = catalog
        self.adapter = adapter
        self.worker_id = worker_id

    async def run_once(self) -> dict[str, Any] | None:
        job = self.catalog.claim_next_execution(self.worker_id)
        if job is None:
            return None
        snapshot = self.catalog.get_snapshot(job["snapshot_id"])
        if snapshot is None:
            self.catalog.set_execution_status(
                job["job_id"], "failed", {"reason": "snapshot_missing"}
            )
            return self.catalog.get_execution_job(job["job_id"])
        try:
            result = (
                await self.adapter.publish(snapshot, job.get("result") or {})
                if job.get("operation") == "publish"
                else await self.adapter.prepare(snapshot)
            )
        except Exception as error:
            self.catalog.set_execution_status(
                job["job_id"],
                "failed",
                {"reason": "adapter_error", "error_type": type(error).__name__},
            )
            return self.catalog.get_execution_job(job["job_id"])
        if result.status == "waiting_user":
            self.catalog.create_intervention(
                job_id=job["job_id"],
                kind=result.intervention_kind or "unknown",
                instruction=result.instruction or "Sprawdź otwarte okno przeglądarki.",
                state=result.evidence,
            )
        else:
            self.catalog.set_execution_status(job["job_id"], result.status, result.evidence)
        return self.catalog.get_execution_job(job["job_id"])

    async def reconcile(self, job_id: str) -> dict[str, Any]:
        job = self.catalog.get_execution_job(job_id)
        if job is None:
            raise KeyError(job_id)
        if job["status"] not in {"unknown", "pending_moderation"}:
            raise PermissionError("only an uncertain outcome can be reconciled")
        snapshot = self.catalog.get_snapshot(job["snapshot_id"])
        assert snapshot is not None
        result = await self.adapter.reconcile(snapshot)
        self.catalog.set_execution_status(job_id, result.status, result.evidence)
        return self.catalog.get_execution_job(job_id)
