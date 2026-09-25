from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

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

ALLOWED_CLICK_TARGETS = {
    "kategoria",
    "wybierz kategorię",
    "zdjęcia",
    "dodaj zdjęcia",
    "stan",
    "wybierz stan",
    "marka",
    "wybierz markę",
    "rozmiar",
    "wybierz rozmiar",
    "kolor",
    "wybierz kolor",
}


@dataclass(frozen=True, slots=True)
class PortalSpec:
    portal: str
    create_url: str
    field_labels: dict[str, tuple[str, ...]]


PORTAL_SPECS = {
    "olx": PortalSpec(
        portal="olx",
        create_url="https://www.olx.pl/d/nowe-ogloszenie/",
        field_labels={
            "title": ("Tytuł ogłoszenia", "Tytuł"),
            "description": ("Opis",),
            "price_pln": ("Cena",),
            "category": ("Kategoria",),
            "photos": ("Zdjęcia", "Dodaj zdjęcia"),
            "condition": ("Stan",),
            "location": ("Lokalizacja",),
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
            "condition": ("Stan",),
            "sale_type": ("Rodzaj ogłoszenia",),
            "location": ("Lokalizacja",),
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


async def detect_page_blocker(page: Page) -> str | None:
    """Return a typed blocker without trying to defeat a portal safeguard."""
    if any(part in page.url.casefold() for part in ("login", "oauth", "signin")):
        return "login_required"
    text = (await page.locator("body").inner_text()).casefold()
    captcha_markers = ("captcha", "nie jestem robotem", "potwierdź, że jesteś człowiekiem")
    if any(marker in text for marker in captcha_markers):
        return "captcha"
    fee_markers = ("opłata za wystawienie", "zapłać za ogłoszenie", "promowanie płatne")
    if any(marker in text for marker in fee_markers):
        return "unexpected_fee"
    return None


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
    return not _is_publish_target(target) and normalized in ALLOWED_CLICK_TARGETS


def _json_safe_form_value(value: Any) -> Any:
    if isinstance(value, Path):
        return {"file_name": value.name}
    if isinstance(value, dict):
        return {str(key): _json_safe_form_value(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe_form_value(child) for child in value]
    return value


def _readback_expected(draft: PortalDraft, photo_paths: list[Path]) -> dict[str, Any]:
    values: dict[str, Any] = {
        "title": draft.title,
        "description": draft.description,
        "price_pln": draft.price_pln,
        "category": draft.category,
        "condition": draft.condition,
        "sale_type": draft.sale_type,
        "location": draft.location,
        "photos": len(photo_paths),
        **{f"delivery.{key}": value for key, value in draft.delivery.items()},
        **{f"attribute.{key}": value for key, value in draft.attributes.items()},
    }
    return {field: value for field, value in values.items() if value not in (None, "", [])}


def _form_values(draft: PortalDraft, photo_paths: list[Path]) -> dict[str, Any]:
    return {
        "title": draft.title,
        "description": draft.description,
        "price_pln": draft.price_pln,
        "category": draft.category,
        "photos": photo_paths,
        "condition": draft.condition,
        "sale_type": draft.sale_type,
        "location": draft.location,
        **{f"delivery.{key}": value for key, value in draft.delivery.items()},
        **{f"attribute.{key}": value for key, value in draft.attributes.items()},
    }


def _field_labels(spec: PortalSpec, field: str) -> tuple[str, ...]:
    fallback = field.split(".", 1)[-1].replace("_", " ")
    return spec.field_labels.get(field, (fallback,))


def _url_matches_portal(url: str, spec: PortalSpec) -> bool:
    actual = (urlsplit(url).hostname or "").casefold().rstrip(".")
    expected = (urlsplit(spec.create_url).hostname or "").casefold().rstrip(".")
    return actual == expected or actual.endswith(f".{expected}")


class SafeActionExecutor:
    """Executes a small action vocabulary and refuses publication-like clicks."""

    async def execute(self, page: Page, action: FormAction, photo_paths: list[Path]) -> None:
        if action.action == "click" and not _is_safe_click_target(action.target):
            raise PermissionError(f"Click outside the allowlist is blocked: {action.target}")
        locator = page.get_by_label(action.target, exact=True)
        if await locator.count() != 1:
            locator = page.get_by_placeholder(action.target, exact=True)
        if await locator.count() != 1:
            raise LookupError(f"Expected exactly one control named {action.target!r}")
        if action.action == "fill":
            await locator.fill(str(action.value or ""))
        elif action.action == "select":
            await locator.select_option(label=str(action.value))
        elif action.action == "check":
            await locator.set_checked(bool(action.value))
        elif action.action == "upload":
            await locator.set_input_files(photo_paths)
        elif action.action == "click":
            await locator.click()


class PortalFormFiller:
    def __init__(self, context: BrowserContext, router: ModelRouter, evidence_dir: Path) -> None:
        self.context = context
        self.router = router
        self.evidence_dir = evidence_dir
        self.executor = SafeActionExecutor()

    async def fill(self, draft: PortalDraft, photo_paths: list[Path]) -> PortalFillResult:
        spec = PORTAL_SPECS[draft.portal]
        page = await self._page_for_portal(spec)
        blocker = await detect_page_blocker(page)
        if blocker:
            return PortalFillResult(
                portal=draft.portal,
                status="needs_user",
                form_url=page.url,
                message=f"intervention:{blocker}",
            )
        filled: dict[str, Any] = {}
        missing: dict[str, Any] = {}
        values = _form_values(draft, photo_paths)
        for field, value in values.items():
            if value in (None, "", []):
                continue
            labels = _field_labels(spec, field)
            success = await self._fill_by_labels(page, field, labels, value, photo_paths)
            if success:
                filled[field] = value if field != "photos" else [path.name for path in photo_paths]
            else:
                missing[field] = value

        if missing:
            repaired = await self._ai_repair(page, missing, photo_paths, draft.portal)
            filled.update(repaired)
            missing = {field: value for field, value in missing.items() if field not in repaired}

        differences = await self._readback(page, draft, filled, photo_paths)
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
            if spec.portal == "olx" and _url_matches_portal(page.url, spec):
                if "/d/nowe-ogloszenie" not in page.url:
                    await page.goto(spec.create_url, wait_until="domcontentloaded", timeout=45_000)
                return page
            if spec.portal == "vinted" and _url_matches_portal(page.url, spec):
                if "/items/new" not in page.url:
                    await page.goto(spec.create_url, wait_until="domcontentloaded", timeout=45_000)
                return page
            if spec.portal == "allegro_lokalnie" and _url_matches_portal(page.url, spec):
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
            try:
                locator = await self._unique_control(page, label)
                if locator is None:
                    continue
                if field == "photos":
                    await locator.set_input_files(photo_paths)
                else:
                    tag = await locator.evaluate("element => element.tagName")
                    input_type = (await locator.get_attribute("type") or "").casefold()
                    if tag == "SELECT":
                        await locator.select_option(label=str(value))
                    elif input_type in {"checkbox", "radio"}:
                        if not isinstance(value, bool):
                            continue
                        await locator.set_checked(value)
                    elif tag in {"INPUT", "TEXTAREA"}:
                        rendered = (
                            str(int(value) if float(value).is_integer() else value)
                            if field == "price_pln"
                            else str(value)
                        )
                        await locator.fill(rendered)
                    else:
                        continue
                return True
            except Exception:
                continue
        return False

    async def _unique_control(self, page: Page, label: str) -> Locator | None:
        by_label = page.get_by_label(label, exact=True)
        if await by_label.count() == 1:
            return by_label
        by_placeholder = page.get_by_placeholder(label, exact=True)
        if await by_placeholder.count() == 1:
            return by_placeholder
        return None

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
                {
                    "portal": portal,
                    "missing": _json_safe_form_value(missing),
                    "controls": controls,
                },
                ensure_ascii=False,
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
        photo_paths: list[Path],
    ) -> dict[str, dict[str, Any]]:
        expected = _readback_expected(draft, photo_paths)
        differences: dict[str, dict[str, Any]] = {}
        spec = PORTAL_SPECS[draft.portal]
        for field, expected_value in expected.items():
            if field not in filled:
                continue
            actual: str | None = None
            for label in _field_labels(spec, field):
                try:
                    locator = await self._unique_control(page, label)
                    if locator is None:
                        continue
                    if field == "photos":
                        actual = str(
                            await locator.evaluate("element => element.files?.length ?? 0")
                        )
                    elif await locator.evaluate("element => element.tagName") == "SELECT":
                        actual = await locator.evaluate(
                            "element => element.selectedOptions[0]?.textContent?.trim() ?? ''"
                        )
                    else:
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
            elif field == "photos":
                if actual != str(expected_value):
                    differences[field] = {"expected": expected_value, "actual": actual}
            elif actual.strip() != str(expected_value).strip():
                differences[field] = {"expected": expected_value, "actual": actual}
        return differences
