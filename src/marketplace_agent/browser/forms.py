from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.async_api import BrowserContext, Locator, Page

from marketplace_agent.domain.models import PortalDraft, PortalFillResult
from marketplace_agent.models.router import ModelRole, ModelRouter
from marketplace_agent.models.tasks import FormAction, FormPlanOutput

FORBIDDEN_ACTION_WORDS = {
    "opublikuj",
    "publikuj",
    "wystaw",
    "sprzedaj",
    "submit",
    "publish",
    "list item",
}

ALLOWED_CLICK_WORDS = {
    "kategori",
    "zdję",
    "stan",
    "mark",
    "rozmiar",
    "kolor",
}


@dataclass(frozen=True, slots=True)
class PortalSpec:
    portal: str
    create_url: str
    field_labels: dict[str, tuple[str, ...]]


PORTAL_SPECS = {
    "olx": PortalSpec(
        portal="olx",
        create_url="https://www.olx.pl/dodaj-ogloszenie/",
        field_labels={
            "title": ("Tytuł ogłoszenia", "Tytuł"),
            "description": ("Opis",),
            "price_pln": ("Cena",),
            "category": ("Kategoria",),
            "photos": ("Zdjęcia", "Dodaj zdjęcia"),
        },
    ),
    "allegro_lokalnie": PortalSpec(
        portal="allegro_lokalnie",
        create_url="https://allegrolokalnie.pl/oferty/wystaw",
        field_labels={
            "title": ("Tytuł", "Co sprzedajesz?"),
            "description": ("Opis",),
            "price_pln": ("Cena",),
            "category": ("Kategoria",),
            "photos": ("Zdjęcia", "Dodaj zdjęcia"),
        },
    ),
    "vinted": PortalSpec(
        portal="vinted",
        create_url="https://www.vinted.pl/items/new",
        field_labels={
            "title": ("Tytuł",),
            "description": ("Opis",),
            "price_pln": ("Cena",),
            "category": ("Kategoria",),
            "photos": ("Zdjęcia", "Dodaj zdjęcia"),
        },
    ),
}

FORM_MAPPING_SYSTEM = """Mapujesz wyłącznie brakujące pola formularza na widoczne
kontrolki. `target` musi być dokładnym tekstem label, aria-label albo placeholder z
listy controls — nigdy indeksem ani selektorem wymyślonym przez model. `value` musi
być dokładną wartością brakującego pola. Nie planuj wysłania, publikacji, przejścia
dalej ani kliknięcia ogólnego przycisku Dodaj. Zwróć tylko konieczne akcje
fill/select/check/upload; click wolno użyć wyłącznie do otwarcia kontrolki konkretnego
pola, np. kategorii, stanu, marki, rozmiaru albo koloru."""


def _is_publish_target(target: str) -> bool:
    normalized = re.sub(r"\s+", " ", target.lower()).strip()
    return any(word in normalized for word in FORBIDDEN_ACTION_WORDS)


def _is_safe_click_target(target: str) -> bool:
    normalized = re.sub(r"\s+", " ", target.lower()).strip()
    return not _is_publish_target(target) and any(
        word in normalized for word in ALLOWED_CLICK_WORDS
    )


class SafeActionExecutor:
    """Executes a small action vocabulary and refuses publication-like clicks."""

    async def execute(self, page: Page, action: FormAction, photo_paths: list[Path]) -> None:
        if action.action == "click" and not _is_safe_click_target(action.target):
            raise PermissionError(f"Click outside the allowlist is blocked: {action.target}")
        locator = page.get_by_label(action.target, exact=False).first
        if action.action == "fill":
            await locator.fill(str(action.value or ""))
        elif action.action == "select":
            await locator.select_option(label=str(action.value))
        elif action.action == "check":
            await locator.set_checked(bool(action.value))
        elif action.action == "upload":
            await locator.set_input_files(photo_paths)
        elif action.action == "click":
            try:
                await locator.click()
            except Exception:
                await page.get_by_text(action.target, exact=False).first.click()


class PortalFormFiller:
    def __init__(self, context: BrowserContext, router: ModelRouter, evidence_dir: Path) -> None:
        self.context = context
        self.router = router
        self.evidence_dir = evidence_dir
        self.executor = SafeActionExecutor()

    async def fill(self, draft: PortalDraft, photo_paths: list[Path]) -> PortalFillResult:
        spec = PORTAL_SPECS[draft.portal]
        page = await self._page_for_portal(spec)
        filled: dict[str, Any] = {}
        missing: dict[str, Any] = {}
        values: dict[str, Any] = {
            "title": draft.title,
            "description": draft.description,
            "price_pln": draft.price_pln,
            "category": draft.category,
            "photos": photo_paths,
            **draft.attributes,
        }
        for field, value in values.items():
            if value in (None, "", []):
                continue
            labels = spec.field_labels.get(field, (field,))
            success = await self._fill_by_labels(page, field, labels, value, photo_paths)
            if success:
                filled[field] = value if field != "photos" else [path.name for path in photo_paths]
            else:
                missing[field] = value

        if missing:
            repaired = await self._ai_repair(page, missing, photo_paths, draft.portal)
            filled.update(repaired)
            missing = {field: value for field, value in missing.items() if field not in repaired}

        differences = await self._readback(page, draft, filled)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        screenshot = self.evidence_dir / f"{draft.portal}-ready.png"
        await page.screenshot(path=screenshot, full_page=True)
        needs_user = bool(missing or differences)
        return PortalFillResult(
            portal=draft.portal,
            status="needs_user" if needs_user else "ready",
            form_url=page.url,
            filled_fields=filled,
            differences=differences,
            screenshot_path=screenshot,
            message=(
                f"Nie udało się potwierdzić pól: {', '.join(sorted(missing))}"
                if missing
                else "Formularz wypełniony i odczytany ponownie. Publikacja pozostaje ręczna."
            ),
        )

    async def _page_for_portal(self, spec: PortalSpec) -> Page:
        for page in self.context.pages:
            if spec.portal == "olx" and "olx.pl" in page.url:
                if "/dodaj-ogloszenie" not in page.url:
                    await page.goto(spec.create_url, wait_until="domcontentloaded", timeout=45_000)
                return page
            if spec.portal == "vinted" and "vinted.pl" in page.url:
                if "/items/new" not in page.url:
                    await page.goto(spec.create_url, wait_until="domcontentloaded", timeout=45_000)
                return page
            if spec.portal == "allegro_lokalnie" and "allegrolokalnie.pl" in page.url:
                if "/oferty/wystaw" not in page.url:
                    await page.goto(spec.create_url, wait_until="domcontentloaded", timeout=45_000)
                return page
        page = await self.context.new_page()
        await page.goto(spec.create_url, wait_until="domcontentloaded", timeout=45_000)
        return page

    async def _fill_by_labels(
        self,
        page: Page,
        field: str,
        labels: tuple[str, ...],
        value: Any,
        photo_paths: list[Path],
    ) -> bool:
        for label in labels:
            locator = page.get_by_label(label, exact=False).first
            try:
                if await locator.count() == 0:
                    continue
                if field == "photos":
                    await locator.set_input_files(photo_paths)
                elif field == "price_pln":
                    await locator.fill(str(int(value) if float(value).is_integer() else value))
                else:
                    await locator.fill(str(value))
                return True
            except Exception:
                continue
        return False

    async def _ai_repair(
        self,
        page: Page,
        missing: dict[str, Any],
        photo_paths: list[Path],
        portal: str,
    ) -> dict[str, Any]:
        screenshot = self.evidence_dir / f"{portal}-fallback.png"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=screenshot, full_page=False)
        controls = await page.locator(
            "input, textarea, select, button, [role=button], [role=combobox]"
        ).evaluate_all(
            """elements => elements.slice(0, 250).map((e, index) => ({
                index,
                tag: e.tagName,
                type: e.type || null,
                name: e.name || null,
                label: e.getAttribute('aria-label') || null,
                placeholder: e.getAttribute('placeholder') || null,
                text: (e.innerText || '').slice(0, 120)
            }))"""
        )
        response = await self.router.run(
            ModelRole.GUI_FALLBACK,
            system=FORM_MAPPING_SYSTEM,
            prompt=json.dumps(
                {"portal": portal, "missing": missing, "controls": controls}, ensure_ascii=False
            ),
            output_schema=FormPlanOutput,
            images=[screenshot],
        )
        repaired: dict[str, Any] = {}
        for action in response.output.actions:
            if action.confidence < 0.75 or (
                action.action == "click" and not _is_safe_click_target(action.target)
            ):
                continue
            try:
                await self.executor.execute(page, action, photo_paths)
            except Exception:
                continue
            for field, value in missing.items():
                if str(value) == str(action.value) or (
                    field == "photos" and action.action == "upload"
                ):
                    repaired[field] = value
        return repaired

    async def _readback(
        self,
        page: Page,
        draft: PortalDraft,
        filled: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        expected = {
            "title": draft.title,
            "description": draft.description,
            "price_pln": draft.price_pln,
        }
        differences: dict[str, dict[str, Any]] = {}
        spec = PORTAL_SPECS[draft.portal]
        for field, expected_value in expected.items():
            if field not in filled:
                continue
            actual: str | None = None
            for label in spec.field_labels[field]:
                locator: Locator = page.get_by_label(label, exact=False).first
                try:
                    if await locator.count():
                        actual = await locator.input_value()
                        break
                except Exception:
                    continue
            if actual is None:
                differences[field] = {"expected": expected_value, "actual": None}
            elif field == "price_pln":
                normalized = re.sub(r"[^0-9,.]", "", actual).replace(",", ".")
                try:
                    if float(normalized) != float(expected_value):
                        differences[field] = {"expected": expected_value, "actual": actual}
                except ValueError:
                    differences[field] = {"expected": expected_value, "actual": actual}
            elif actual.strip() != str(expected_value).strip():
                differences[field] = {"expected": expected_value, "actual": actual}
        return differences
