import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from marketplace_agent.domain.catalog import CatalogRepository
from marketplace_agent.domain.models import (
    FactProposal,
    ItemCase,
    PortalDraft,
    PortalFillResult,
    PriceRecommendation,
    PriceResearchSummary,
    WorkflowStatus,
)
from marketplace_agent.models.ollama_provider import StaticModelProvider
from marketplace_agent.models.router import ModelRole, ModelRouter, RoleConfig, RouterConfig
from marketplace_agent.models.tasks import (
    CopyAuditItem,
    CopyAuditOutput,
    CopyDraftOutput,
    FactExtractionOutput,
    PortalRecommendationOutput,
)
from marketplace_agent.workflow.dependencies import WorkflowDependencies
from marketplace_agent.workflow.graph import build_graph


class ResearchStub:
    async def run(self, facts, *, item_id=None, run_id=None):
        return PriceResearchSummary(
            checked_count=10,
            reachable_count=9,
            comparable_count=8,
            median_pln=100,
            exact_price_counts=[],
            recommendations=[PriceRecommendation(strategy="market", price_pln=100, basis="median")],
        )


class BrowserStub:
    async def fill_all(self, item_id, drafts, photo_paths):
        return [PortalFillResult(portal=drafts[0].portal, status="ready")]


class BrowserMustNotRunInGraph:
    async def fill_all(self, item_id, drafts, photo_paths):
        raise AssertionError("browser execution belongs to the separate worker")


def approved_response(catalog, value):
    record = catalog.issue_approval(
        channel_id="test",
        item_id=value["item_id"],
        step=value["kind"],
        payload=value,
        snapshot_ids=list(value.get("snapshot_ids", {}).values()),
    )
    consumed = catalog.consume_approval(
        token=record["token"],
        channel_id="test",
        item_id=value["item_id"],
        expected_step=value["kind"],
    )
    return {"action": "accept", "approval_id": consumed["approval_id"]}


def interrupt_kind(result):
    return result["__interrupt__"][0].value["kind"]


def test_vinted_is_not_an_execution_portal() -> None:
    from marketplace_agent.workflow.graph import EXECUTION_PORTALS

    assert {"olx", "allegro_lokalnie"} == EXECUTION_PORTALS


@pytest.mark.asyncio
async def test_graph_pauses_before_each_human_decision(tmp_path) -> None:
    provider = StaticModelProvider(
        {
            FactExtractionOutput: FactExtractionOutput(
                facts=[
                    FactProposal(name="category", value="lampa", confidence=0.9, source="image"),
                    FactProposal(name="condition", value="używana", confidence=0.7, source="model"),
                ]
            ),
            PortalRecommendationOutput: PortalRecommendationOutput(
                portals=["olx"], reasons={"olx": "lokalny odbiór"}
            ),
            CopyDraftOutput: CopyDraftOutput(
                drafts=[
                    PortalDraft(
                        portal="olx",
                        title="Lampa",
                        description="Używana lampa.",
                        category="Dom",
                        price_pln=100,
                    )
                ]
            ),
            CopyAuditOutput: CopyAuditOutput(decisions=[CopyAuditItem(portal="olx", safe=True)]),
        }
    )
    router = ModelRouter(
        provider,
        RouterConfig(roles={role: RoleConfig(model="static") for role in ModelRole}),
    )
    catalog = CatalogRepository(tmp_path / "catalog.sqlite")
    catalog.setup()
    graph = build_graph(
        WorkflowDependencies(router, ResearchStub(), BrowserStub(), catalog), InMemorySaver()
    )
    photo = tmp_path / "fixture.jpg"
    photo.write_bytes(b"fixture")
    item = ItemCase(photo_paths=[photo])
    config = {"configurable": {"thread_id": item.item_id}}

    result = await graph.ainvoke({"item": item.model_dump(mode="json")}, config=config)
    assert interrupt_kind(result) == "fact"
    result = await graph.ainvoke(Command(resume={"action": "accept"}), config=config)
    assert interrupt_kind(result) == "fact"
    result = await graph.ainvoke(Command(resume={"action": "accept"}), config=config)
    assert interrupt_kind(result) == "portals"
    result = await graph.ainvoke(Command(resume={"action": "accept"}), config=config)
    assert interrupt_kind(result) == "price"
    result = await graph.ainvoke(Command(resume={"action": "accept"}), config=config)
    assert interrupt_kind(result) == "copy"
    result = await graph.ainvoke(Command(resume={"action": "accept"}), config=config)
    assert interrupt_kind(result) == "fill_authorization"
    response = approved_response(catalog, result["__interrupt__"][0].value)
    result = await graph.ainvoke(Command(resume=response), config=config)

    finished = ItemCase.model_validate(result["item"])
    assert finished.status == WorkflowStatus.FORM_FILLING
    assert finished.portal_drafts[0].approved
    assert catalog.list_execution_jobs(item.item_id)[0]["status"] == "queued"


@pytest.mark.asyncio
async def test_graph_does_not_open_browser_in_orchestrator_process(tmp_path) -> None:
    provider = StaticModelProvider(
        {
            FactExtractionOutput: FactExtractionOutput(
                facts=[FactProposal(name="category", value="lampa", confidence=0.9, source="image")]
            ),
            PortalRecommendationOutput: PortalRecommendationOutput(
                portals=["olx"], reasons={"olx": "lokalny odbiór"}
            ),
            CopyDraftOutput: CopyDraftOutput(
                drafts=[
                    PortalDraft(
                        portal="olx",
                        title="Lampa",
                        description="Używana lampa.",
                        category="Dom",
                        price_pln=100,
                    )
                ]
            ),
            CopyAuditOutput: CopyAuditOutput(decisions=[CopyAuditItem(portal="olx", safe=True)]),
        }
    )
    router = ModelRouter(
        provider,
        RouterConfig(roles={role: RoleConfig(model="static") for role in ModelRole}),
    )
    catalog = CatalogRepository(tmp_path / "catalog.sqlite")
    catalog.setup()
    graph = build_graph(
        WorkflowDependencies(router, ResearchStub(), BrowserMustNotRunInGraph(), catalog),
        InMemorySaver(),
    )
    photo = tmp_path / "fixture.jpg"
    photo.write_bytes(b"fixture")
    item = ItemCase(photo_paths=[photo])
    config = {"configurable": {"thread_id": item.item_id}}
    result = await graph.ainvoke({"item": item.model_dump(mode="json")}, config=config)
    for _ in range(4):
        result = await graph.ainvoke(Command(resume={"action": "accept"}), config=config)
    response = approved_response(catalog, result["__interrupt__"][0].value)
    result = await graph.ainvoke(Command(resume=response), config=config)
    finished = ItemCase.model_validate(result["item"])
    assert finished.status == WorkflowStatus.FORM_FILLING
    assert result["execution_job_ids"]
