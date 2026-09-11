import json

import pytest

from marketplace_agent.domain.models import ComparableCandidate
from marketplace_agent.domain.pricing import summarize_prices
from marketplace_agent.research.config import ResearchConfig, ResearchLimits
from marketplace_agent.research.evidence import write_research_manifest
from marketplace_agent.research.service import MarketResearchService


def candidate() -> ComparableCandidate:
    return ComparableCandidate(
        source="olx",
        url="https://www.olx.pl/d/oferta/example",
        title="Nintendo Switch OLED",
        price_pln=1100,
        currency="PLN",
        price_kind="item",
        status="active",
        verified=True,
        comparable=True,
        integrity_status="consistent",
        evidence_channels=["olx_primary_dom"],
    )


def test_manifest_preserves_pricing_decisions_without_page_content(tmp_path) -> None:
    rows = [candidate()]
    summary = summarize_prices(rows)
    relative_path = write_research_manifest(tmp_path, "item_123", rows, summary)
    target = tmp_path / relative_path
    payload = json.loads(target.read_text(encoding="utf-8"))

    assert relative_path == "items/item_123/evidence/research.json"
    assert payload["candidates"][0]["price_amount"] == 1100
    assert payload["candidates"][0]["evidence_channels"] == ["olx_primary_dom"]
    assert payload["summary"]["recommendation_basis"] == "active_asking_prices"
    assert "html" not in target.read_text(encoding="utf-8").casefold()
    assert target.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("item_id", ["../escape", "a/b", "", "x" * 65])
def test_manifest_rejects_unsafe_item_id(tmp_path, item_id) -> None:
    with pytest.raises(ValueError):
        write_research_manifest(tmp_path, item_id, [], summarize_prices([]))


@pytest.mark.asyncio
async def test_research_service_attaches_written_manifest(tmp_path, monkeypatch) -> None:
    row = candidate()
    service = MarketResearchService(
        browser=None,
        router=None,
        config=ResearchConfig(research=ResearchLimits(), sources=[]),
        data_dir=tmp_path,
    )

    async def fake_run_bounded(facts):
        service._progress_candidates = [row]
        return summarize_prices([row])

    monkeypatch.setattr(service, "_run_bounded", fake_run_bounded)
    summary = await service.run({"model": "OLED"}, item_id="case_1")

    assert summary.evidence_manifest_path == "items/case_1/evidence/research.json"
    assert (tmp_path / summary.evidence_manifest_path).is_file()
