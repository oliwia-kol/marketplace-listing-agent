import json
from pathlib import Path

import pytest

from marketplace_agent.evaluation.runner import EvaluationRunner
from marketplace_agent.models.base import StructuredModelResponse
from marketplace_agent.models.router import ModelRole, ModelRouter, RoleConfig, RouterConfig
from marketplace_agent.models.tasks import CopyTextOutput


class BriefEchoProvider:
    async def structured(self, *, model: str, prompt: str, output_schema, **kwargs):
        brief = json.loads(prompt)
        description = ". ".join(claim["value"] for claim in brief["claims"])
        drafts = [
            {"portal": portal, "title": f"Oferta {portal}", "description": description}
            for portal in brief["portals"]
        ]
        output = CopyTextOutput.model_validate({"drafts": drafts})
        return StructuredModelResponse(output=output, model=model)

    async def unload(self, model: str) -> None:
        return None

    async def available_models(self) -> list[str]:
        return ["echo"]


@pytest.mark.asyncio
async def test_copy_eval_can_select_split_limit_and_repeats(tmp_path: Path) -> None:
    config = RouterConfig(
        roles={role: RoleConfig(model="echo", fallback=None) for role in ModelRole}
    )
    runner = EvaluationRunner(
        ModelRouter(BriefEchoProvider(), config),
        Path("goldens"),
        tmp_path,
    )

    report_path = await runner.run(
        "copy_quality",
        split="selection",
        limit=2,
        case_ids={
            "copy-quality-nintendo-switch-oled-20",
            "copy-quality-nintendo-switch-oled-22",
        },
        repeats=2,
        generation_overrides={"seed": 7},
    )
    report = json.loads(report_path.read_text())

    assert report["total"] == 4
    assert report["pass_rate"] == 1
    assert report["aggregate_metrics"]["schema_valid"] == 1
    assert report["evaluation_scope"]["effective_role_config"]["seed"] == 7
    assert report["evaluation_scope"]["case_ids"] == [
        "copy-quality-nintendo-switch-oled-20",
        "copy-quality-nintendo-switch-oled-22",
    ]
    assert report["latency_seconds"]["p95"] >= 0
    assert all("#run-" in result["case_id"] for result in report["results"])
