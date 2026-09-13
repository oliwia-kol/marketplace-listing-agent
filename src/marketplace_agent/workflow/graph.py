from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from marketplace_agent.domain.category_profiles import redact_sensitive_facts
from marketplace_agent.domain.copy_safety import obvious_unsupported_claims, safe_template
from marketplace_agent.domain.models import FactProposal, ItemCase, PortalDraft, WorkflowStatus
from marketplace_agent.models.router import ModelRole
from marketplace_agent.models.tasks import (
    CopyAuditOutput,
    CopyDraftOutput,
    FactExtractionOutput,
    PortalRecommendationOutput,
)
from marketplace_agent.workflow.dependencies import WorkflowDependencies
from marketplace_agent.workflow.state import ListingState, approval_value

FACT_SYSTEM = """Analizujesz zdjęcia przedmiotu przeznaczonego do sprzedaży.
Wypisz wyłącznie cechy widoczne lub podane przez użytkownika. Nie zgaduj marki,
modelu, stanu, rozmiaru ani kompletności. Każdy fakt ma confidence i źródło.
Pytania o brakujące informacje zwróć osobno. Nazwy pól zapisuj wyłącznie jako:
category, brand, model, color, condition, defects, size, material, dimensions,
completeness, accessories, identifiers albo attribute.<snake_case>. Wartości mogą
być po polsku. Nie poprzedzaj pól kanonicznych prefiksem attribute. Nie zwracaj pól,
o których brak informacji; słowa „nieznany” i „nieokreślony” nie są faktami. Stan
przedmiotu podaj tylko wtedy, gdy użytkownik podał go wprost. Dodatkowe dane techniczne,
np. mount, model_code, region, format, chip i storage, zapisuj jako attribute.*.
Odpowiadaj zgodnie ze schematem."""

PORTAL_SYSTEM = """Dobierasz polskie portale sprzedażowe do konkretnego przedmiotu.
Możesz wybrać wyłącznie OLX lub Allegro Lokalnie. Uwzględnij kategorię, prawdopodobną
grupę kupujących i wygodę sprzedaży. Nie zmieniaj faktów o produkcie."""

COPY_SYSTEM = """Piszesz rzetelne polskie ogłoszenia sprzedażowe. Przygotuj osobny
tekst dla każdego wybranego portalu. Każde twierdzenie w tytule, opisie i atrybutach
musi wynikać wprost z wejściowego słownika facts. Nie wolno dopisywać typowych cech
produktu ani wnioskować z marki/modelu. W szczególności nie wymyślaj wymiarów, stanu,
sprawności, przeznaczenia, kroju, zapięcia, podszewki, akcesoriów ani kompletności.
Nie pisz „idealny”, „bez wad” ani „bez śladów”, jeśli tego nie ma w facts. Pominięcie
informacji jest poprawne; zgadywanie jest błędem. Wady opisuj jasno. Bez danych
kontaktowych. Cena musi być dokładnie ceną zaakceptowaną przez użytkownika."""

COPY_AUDIT_SYSTEM = """Jesteś rygorystycznym audytorem ogłoszeń. Porównaj każde
twierdzenie w draftach z zatwierdzonym słownikiem facts. Typowe cechy produktu,
sprawność, wymiary, stan, zastosowanie, odbiór i akcesoria są niedozwolone, jeśli nie
widnieją w facts. Zwróć dokładnie jedną decyzję dla każdego portalu obecnego w
wejściowej liście drafts i żadnych decyzji dla innych portali. Wypisz niepoparte
twierdzenia."""

EXECUTION_PORTALS = {"olx", "allegro_lokalnie"}


def _item(state: ListingState) -> ItemCase:
    return ItemCase.model_validate(state["item"])


def _save(deps: WorkflowDependencies, item: ItemCase) -> dict[str, Any]:
    deps.catalog.save_item(item)
    return item.model_dump(mode="json")


def build_graph(deps: WorkflowDependencies, checkpointer: Any = None):
    """Build the workflow. All irreversible decisions are behind interrupts."""

    async def analyze_item(state: ListingState) -> ListingState:
        item = _item(state)
        run_id = state.get("run_id") or uuid4().hex
        response = await deps.router.run(
            ModelRole.VISION_FAST,
            system=FACT_SYSTEM,
            prompt=(
                "Notatki użytkownika:\n"
                f"{state.get('user_notes', '') or '(brak)'}\n"
                "Zwróć cechy przydatne do identyfikacji, wyceny i ogłoszenia."
            ),
            output_schema=FactExtractionOutput,
            images=item.photo_paths,
            run_id=run_id,
            item_id=item.item_id,
        )
        item.facts.proposals = response.output.facts
        profile_catalog = getattr(deps.research, "category_profiles", None)
        profile_facts = {fact.name: fact.value for fact in item.facts.proposals}
        profile_facts["user_context"] = state.get("user_notes", "")
        profile = profile_catalog.match(profile_facts) if profile_catalog else None
        item.status = WorkflowStatus.FACTS_REVIEW
        return {
            "item": _save(deps, item),
            "run_id": run_id,
            "missing_questions": list(
                dict.fromkeys(
                    response.output.missing_questions + (profile.questions if profile else [])
                )
            ),
        }

    async def review_facts(state: ListingState) -> ListingState:
        item = _item(state)
        for fact in item.facts.proposals:
            original_value = fact.value
            response = interrupt(
                {
                    "kind": "fact",
                    "item_id": item.item_id,
                    "field": fact.name,
                    "value": fact.value,
                    "confidence": fact.confidence,
                    "source": fact.source,
                    "question": f"Czy zatwierdzasz pole „{fact.name}”?",
                }
            )
            approved, value = approval_value(response, fact.value)
            if not approved:
                raise ValueError(f"Nieobsługiwana odpowiedź zatwierdzenia: {response!r}")
            fact.value = value
            fact.source = "user" if value != original_value else fact.source
            fact.approved = True
        return {"item": _save(deps, item)}

    async def recommend_portals(state: ListingState) -> ListingState:
        item = _item(state)
        response = await deps.router.run(
            ModelRole.VISION_FAST,
            system=PORTAL_SYSTEM,
            prompt=json.dumps(item.facts.approved_dict(), ensure_ascii=False),
            output_schema=PortalRecommendationOutput,
            run_id=state.get("run_id"),
            item_id=item.item_id,
        )
        item.recommended_portals = list(dict.fromkeys(response.output.portals))
        item.recommended_portals = [
            portal for portal in item.recommended_portals if portal in EXECUTION_PORTALS
        ]
        if not item.recommended_portals:
            raise ValueError("Model nie wskazał obsługiwanego portalu wykonawczego")
        item.status = WorkflowStatus.PORTALS_REVIEW
        return {
            "item": _save(deps, item),
            "portal_reasons": response.output.reasons,
        }

    async def review_missing_info(state: ListingState) -> ListingState:
        questions = state.get("missing_questions", [])
        if not questions:
            return {}
        item = _item(state)
        for offset in range(0, len(questions), 3):
            response = interrupt(
                {
                    "kind": "missing_info",
                    "item_id": item.item_id,
                    "questions": questions[offset : offset + 3],
                    "question": (
                        "Możesz dodać brakujące fakty jako JSON albo zaakceptować pominięcie."
                    ),
                }
            )
            if isinstance(response, dict) and response.get("action") == "edit":
                values = response.get("value", {})
                if not isinstance(values, dict):
                    raise ValueError("Brakujące fakty muszą być obiektem JSON")
                for name, value in values.items():
                    item.facts.proposals.append(
                        FactProposal(
                            name=name,
                            value=value,
                            confidence=1,
                            source="user",
                            approved=True,
                        )
                    )
            elif not (isinstance(response, dict) and response.get("action") == "accept"):
                raise ValueError("Brakujące informacje wymagają decyzji")
        return {"item": _save(deps, item), "missing_questions": []}

    async def review_portals(state: ListingState) -> ListingState:
        item = _item(state)
        response = interrupt(
            {
                "kind": "portals",
                "item_id": item.item_id,
                "recommended": item.recommended_portals,
                "reasons": state.get("portal_reasons", {}),
                "question": "Które portale zatwierdzasz?",
            }
        )
        selected = item.recommended_portals
        if isinstance(response, dict):
            if response.get("action") == "edit":
                selected = list(response.get("value", []))
            elif response.get("action") != "accept":
                raise ValueError(f"Nieobsługiwana odpowiedź: {response!r}")
        elif response != "accept":
            raise ValueError(f"Nieobsługiwana odpowiedź: {response!r}")
        unsupported = set(selected) - EXECUTION_PORTALS
        if unsupported:
            raise ValueError(f"Portale wyłączone z wykonania: {sorted(unsupported)}")
        item.selected_portals = selected
        item.status = WorkflowStatus.MARKET_RESEARCH
        return {"item": _save(deps, item)}

    async def research_price(state: ListingState) -> ListingState:
        item = _item(state)
        item.price_summary = await deps.research.run(
            item.facts.approved_dict(), item_id=item.item_id, run_id=state.get("run_id")
        )
        item.status = WorkflowStatus.PRICE_REVIEW
        return {"item": _save(deps, item)}

    async def review_price(state: ListingState) -> ListingState:
        item = _item(state)
        summary = item.price_summary
        if summary is None:
            raise RuntimeError("Brak wyniku badania ceny")
        response = interrupt(
            {
                "kind": "price",
                "item_id": item.item_id,
                "summary": summary.model_dump(mode="json"),
                "question": "Wybierz rekomendację albo wpisz własną cenę.",
            }
        )
        market = next(
            (row.price_pln for row in summary.recommendations if row.strategy == "market"),
            None,
        )
        approved, value = approval_value(response, market)
        if not approved or value is None:
            raise ValueError("Cena wymaga jawnej akceptacji")
        item.selected_price_pln = float(value)
        return {"item": _save(deps, item)}

    async def draft_copy(state: ListingState) -> ListingState:
        item = _item(state)
        public_facts = redact_sensitive_facts(item.facts.approved_dict())
        response = await deps.router.run(
            ModelRole.POLISH_COPYWRITER,
            system=COPY_SYSTEM,
            prompt=json.dumps(
                {
                    "facts": public_facts,
                    "portals": item.selected_portals,
                    "price_pln": item.selected_price_pln,
                    "preferences": deps.catalog.list_preferences(
                        str(item.facts.approved_dict().get("category", "")) or None
                    )[:20],
                },
                ensure_ascii=False,
            ),
            output_schema=CopyDraftOutput,
            run_id=state.get("run_id"),
            item_id=item.item_id,
        )
        requested = set(item.selected_portals)
        item.portal_drafts = [
            draft for draft in response.output.drafts if draft.portal in requested
        ]
        returned = {draft.portal for draft in item.portal_drafts}
        if returned != requested:
            raise ValueError(
                f"Model nie przygotował tekstów dla portali: {sorted(requested - returned)}"
            )
        for draft in item.portal_drafts:
            draft.price_pln = float(item.selected_price_pln)
            draft.condition = (
                str(public_facts["condition"])
                if public_facts.get("condition") is not None
                else None
            )
            # Transaction and location choices belong to the user, never to the copy model.
            draft.sale_type = None
            draft.location = None
            draft.delivery = {}
            draft.approved = False
            approved_values = {str(value).casefold() for value in public_facts.values()}
            draft.attributes = {
                key: value
                for key, value in draft.attributes.items()
                if str(value).casefold() in approved_values
            }
        item.status = WorkflowStatus.COPY_REVIEW
        return {"item": _save(deps, item)}

    async def audit_copy(state: ListingState) -> ListingState:
        item = _item(state)
        facts = redact_sensitive_facts(item.facts.approved_dict())
        response = await deps.router.run(
            ModelRole.MARKET_EXPERT,
            system=COPY_AUDIT_SYSTEM,
            prompt=json.dumps(
                {
                    "facts": facts,
                    "drafts": [draft.model_dump(mode="json") for draft in item.portal_drafts],
                },
                ensure_ascii=False,
            ),
            output_schema=CopyAuditOutput,
            run_id=state.get("run_id"),
            item_id=item.item_id,
        )
        decisions = {decision.portal: decision for decision in response.output.decisions}
        warnings: dict[str, list[str]] = {}
        safe_drafts: list[PortalDraft] = []
        for draft in item.portal_drafts:
            deterministic = obvious_unsupported_claims(draft, facts)
            decision = decisions.get(draft.portal)
            model_findings = decision.unsupported_claims if decision else ["brak decyzji audytora"]
            findings = sorted(set(deterministic + model_findings))
            if decision is None or not decision.safe or findings:
                warnings[draft.portal] = findings
                safe_drafts.append(safe_template(draft, facts))
            else:
                safe_drafts.append(draft)
        item.portal_drafts = safe_drafts
        return {"item": _save(deps, item), "copy_warnings": warnings}

    async def review_copy(state: ListingState) -> ListingState:
        item = _item(state)
        for draft in item.portal_drafts:
            original = draft.model_dump(mode="json")
            response = interrupt(
                {
                    "kind": "copy",
                    "item_id": item.item_id,
                    "portal": draft.portal,
                    "draft": original,
                    "warnings": state.get("copy_warnings", {}).get(draft.portal, []),
                    "question": f"Czy zatwierdzasz treść dla {draft.portal}?",
                }
            )
            approved, value = approval_value(response, original)
            if not approved:
                raise ValueError("Treść wymaga jawnej akceptacji")
            if isinstance(value, dict):
                edited = PortalDraft.model_validate({**original, **value, "approved": True})
                changed = {
                    key: {"before": original[key], "after": edited.model_dump(mode="json")[key]}
                    for key in ("title", "description", "category")
                    if original[key] != edited.model_dump(mode="json")[key]
                }
                if changed:
                    deps.catalog.save_preference("copy_edit", changed, category=edited.category)
                draft.title = edited.title
                draft.description = edited.description
                draft.category = edited.category
                draft.condition = edited.condition
                draft.sale_type = edited.sale_type
                draft.location = edited.location
                draft.delivery = edited.delivery
                draft.attributes = edited.attributes
            draft.approved = True
        item.snapshot_ids = {
            draft.portal: deps.catalog.create_listing_snapshot(item, draft)
            for draft in item.portal_drafts
        }
        return {"item": _save(deps, item)}

    async def authorize_fill(state: ListingState) -> ListingState:
        item = _item(state)
        previews = []
        for portal, snapshot_id in item.snapshot_ids.items():
            snapshot = deps.catalog.get_snapshot(snapshot_id)
            if snapshot:
                previews.append(
                    {
                        "portal": portal,
                        "snapshot_id": snapshot_id,
                        "version": snapshot["version"],
                        "content_hash": snapshot["content_hash"][:16],
                        "draft": snapshot["payload"]["draft"],
                        "photos": [
                            {"name": photo["file_name"], "sha256": photo["sha256"][:16]}
                            for photo in snapshot["payload"]["photos"]
                        ],
                    }
                )
        response = interrupt(
            {
                "kind": "fill_authorization",
                "item_id": item.item_id,
                "portals": item.selected_portals,
                "snapshot_ids": item.snapshot_ids,
                "previews": previews,
                "question": "Wypełnić formularze w Chrome? Bot nie kliknie publikacji.",
            }
        )
        approved, _ = approval_value(response, True)
        if not approved:
            raise ValueError("Wypełnianie formularzy wymaga jawnej akceptacji")
        approval_id = response.get("approval_id") if isinstance(response, dict) else None
        if not approval_id or not deps.catalog.validate_consumed_approval(
            approval_id,
            item.item_id,
            "fill_authorization",
            list(item.snapshot_ids.values()),
        ):
            raise PermissionError("Zgoda nie odpowiada bieżącym snapshotom")
        item.status = WorkflowStatus.FORM_FILLING
        return {"item": _save(deps, item), "fill_approval_id": approval_id}

    async def fill_forms(state: ListingState) -> ListingState:
        item = _item(state)
        approval_id = state.get("fill_approval_id")
        if not approval_id:
            raise PermissionError("Brak zgody wykonawczej w stanie grafu")
        jobs = [
            deps.catalog.enqueue_execution(
                approval_id=approval_id,
                snapshot_id=snapshot_id,
                portal=portal,
            )
            for portal, snapshot_id in item.snapshot_ids.items()
        ]
        item.status = WorkflowStatus.FORM_FILLING
        return {
            "item": _save(deps, item),
            "execution_job_ids": [job["job_id"] for job in jobs],
        }

    builder = StateGraph(ListingState)
    builder.add_node("analyze_item", analyze_item)
    builder.add_node("review_facts", review_facts)
    builder.add_node("review_missing_info", review_missing_info)
    builder.add_node("recommend_portals", recommend_portals)
    builder.add_node("review_portals", review_portals)
    builder.add_node("research_price", research_price)
    builder.add_node("review_price", review_price)
    builder.add_node("draft_copy", draft_copy)
    builder.add_node("audit_copy", audit_copy)
    builder.add_node("review_copy", review_copy)
    builder.add_node("authorize_fill", authorize_fill)
    builder.add_node("fill_forms", fill_forms)
    builder.add_edge(START, "analyze_item")
    builder.add_edge("analyze_item", "review_facts")
    builder.add_edge("review_facts", "review_missing_info")
    builder.add_edge("review_missing_info", "recommend_portals")
    builder.add_edge("recommend_portals", "review_portals")
    builder.add_edge("review_portals", "research_price")
    builder.add_edge("research_price", "review_price")
    builder.add_edge("review_price", "draft_copy")
    builder.add_edge("draft_copy", "audit_copy")
    builder.add_edge("audit_copy", "review_copy")
    builder.add_edge("review_copy", "authorize_fill")
    builder.add_edge("authorize_fill", "fill_forms")
    builder.add_edge("fill_forms", END)
    return builder.compile(checkpointer=checkpointer)
