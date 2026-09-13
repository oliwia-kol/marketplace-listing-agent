from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

from marketplace_agent.browser.forms import FORM_MAPPING_SYSTEM, _is_safe_click_target
from marketplace_agent.domain.models import ComparableCandidate
from marketplace_agent.domain.pricing import summarize_prices
from marketplace_agent.evaluation.metrics import classification_metrics, set_metrics
from marketplace_agent.models.router import ModelRole, ModelRouter
from marketplace_agent.models.tasks import (
    ComparableAuditOutput,
    CopyAuditOutput,
    CopyDraftOutput,
    FactExtractionOutput,
    FormPlanOutput,
)
from marketplace_agent.research.service import AUDIT_SYSTEM
from marketplace_agent.workflow.graph import COPY_AUDIT_SYSTEM, COPY_SYSTEM, FACT_SYSTEM


@dataclass(slots=True)
class CaseResult:
    case_id: str
    passed: bool
    metrics: dict[str, float]
    telemetry: dict[str, float]
    latency_seconds: float
    model: str
    output: Any | None
    error: str | None = None


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _normalized(value: Any) -> str:
    return " ".join(str(value).casefold().split())


class EvaluationRunner:
    def __init__(self, router: ModelRouter, goldens_dir: Path, reports_dir: Path) -> None:
        self.router = router
        self.goldens_dir = goldens_dir
        self.reports_dir = reports_dir

    async def run(self, suite: str, model_override: str | None = None) -> Path:
        if suite == "price_math":
            results = self._price_math()
        elif suite in {"facts", "comparables", "copy", "copy_audit", "forms"}:
            results = await self._model_suite(suite, model_override)
        else:
            raise ValueError(f"Nieznany zestaw: {suite}")
        return self._write_report(suite, results)

    def _price_math(self) -> list[CaseResult]:
        results: list[CaseResult] = []
        for row in load_jsonl(self.goldens_dir / "price_math.jsonl"):
            started = time.perf_counter()
            candidates = [
                ComparableCandidate(
                    source=item.get("source", "fixture"),
                    url=f"https://example.test/{row['id']}/{index}",
                    title=f"Fixture {index}",
                    price_pln=item["price_pln"],
                    currency=item.get("currency", "PLN"),
                    price_kind=item.get("price_kind", "item"),
                    status=item.get("status", "active"),
                    verified=item.get("verified", True),
                    comparable=item.get("comparable", True),
                    integrity_status=item.get("integrity_status", "consistent"),
                )
                for index, item in enumerate(row["candidates"])
            ]
            summary = summarize_prices(candidates)
            expected = row["expected"]
            checks = {key: float(getattr(summary, key) == value) for key, value in expected.items()}
            results.append(
                CaseResult(
                    case_id=row["id"],
                    passed=all(checks.values()),
                    metrics=checks,
                    telemetry={},
                    latency_seconds=time.perf_counter() - started,
                    model="deterministic",
                    output=summary.model_dump(mode="json"),
                )
            )
        return results

    async def _model_suite(self, suite: str, model_override: str | None) -> list[CaseResult]:
        path = self.goldens_dir / f"{suite}.jsonl"
        results: list[CaseResult] = []
        role = {
            "facts": ModelRole.VISION_FAST,
            "comparables": ModelRole.MARKET_EXPERT,
            "copy": ModelRole.POLISH_COPYWRITER,
            "copy_audit": ModelRole.MARKET_EXPERT,
            "forms": ModelRole.GUI_FALLBACK,
        }[suite]
        original = self.router.config.roles[role].model
        original_fallback = self.router.config.roles[role].fallback
        if model_override:
            self.router.config.roles[role].model = model_override
        # Benchmarks must measure the selected model. A silent fallback would make
        # two runs incomparable while still looking successful.
        self.router.config.roles[role].fallback = None
        try:
            for row in load_jsonl(path):
                started = time.perf_counter()
                memory_before = psutil.Process().memory_info().rss
                try:
                    result = await self._run_case(suite, role, row)
                    result.latency_seconds = time.perf_counter() - started
                    result.telemetry["python_rss_delta_mb"] = (
                        psutil.Process().memory_info().rss - memory_before
                    ) / 1_048_576
                except Exception as error:
                    result = CaseResult(
                        case_id=row["id"],
                        passed=False,
                        metrics={"schema_valid": 0.0},
                        telemetry={},
                        latency_seconds=time.perf_counter() - started,
                        model=self.router.config.roles[role].model,
                        output=None,
                        error=type(error).__name__,
                    )
                results.append(result)
        finally:
            self.router.config.roles[role].model = original
            self.router.config.roles[role].fallback = original_fallback
        return results

    async def _run_case(self, suite: str, role: ModelRole, row: dict[str, Any]) -> CaseResult:
        if suite == "facts":
            response = await self.router.run(
                role,
                system=FACT_SYSTEM,
                prompt=f"Notatki użytkownika:\n{row['notes']}",
                output_schema=FactExtractionOutput,
            )
            facts_by_name = {fact.name: fact.value for fact in response.output.facts}
            metrics = set_metrics(set(row["expected_fields"]), set(facts_by_name))
            forbidden = [_normalized(value) for value in row.get("forbidden_values", [])]
            rendered_values = [_normalized(value) for value in facts_by_name.values()]
            metrics["hallucination_guard"] = float(
                not any(phrase in value for phrase in forbidden for value in rendered_values)
            )
            expected_values = row.get("expected_values", {})
            if expected_values:
                correct_values = [
                    _normalized(facts_by_name.get(name)) == _normalized(expected)
                    for name, expected in expected_values.items()
                ]
                metrics["value_accuracy"] = sum(correct_values) / len(correct_values)
        elif suite == "comparables":
            response = await self.router.run(
                role,
                system=AUDIT_SYSTEM,
                prompt=json.dumps(row["input"], ensure_ascii=False),
                output_schema=ComparableAuditOutput,
            )
            ordered = sorted(response.output.decisions, key=lambda value: value.index)
            expected = row["expected_comparable"]
            actual = [decision.comparable for decision in ordered]
            metrics = (
                classification_metrics(expected, actual)
                if len(actual) == len(expected)
                else {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}
            )
        elif suite == "copy":
            response = await self.router.run(
                role,
                system=COPY_SYSTEM,
                prompt=json.dumps(row["input"], ensure_ascii=False),
                output_schema=CopyDraftOutput,
            )
            text = " ".join(
                f"{draft.title} {draft.description}" for draft in response.output.drafts
            ).lower()
            required = [value.lower() for value in row["required_phrases"]]
            forbidden = [value.lower() for value in row["forbidden_phrases"]]
            metrics = {
                "required_fact_recall": sum(value in text for value in required) / len(required),
                "hallucination_guard": float(not any(value in text for value in forbidden)),
                "portal_coverage": len({draft.portal for draft in response.output.drafts})
                / len(row["input"]["portals"]),
            }
        elif suite == "copy_audit":
            response = await self.router.run(
                role,
                system=COPY_AUDIT_SYSTEM,
                prompt=json.dumps(row["input"], ensure_ascii=False),
                output_schema=CopyAuditOutput,
            )
            ordered = sorted(response.output.decisions, key=lambda value: value.portal)
            expected = row["expected_safe"]
            by_portal = {decision.portal: decision.safe for decision in ordered}
            expected_portals_in_order = [draft["portal"] for draft in row["input"]["drafts"]]
            actual = [by_portal.get(portal) for portal in expected_portals_in_order]
            correct = float(len(actual) == len(expected) and actual == expected)
            expected_portals = {draft["portal"] for draft in row["input"]["drafts"]}
            actual_portals = {decision.portal for decision in ordered}
            metrics = {
                "accuracy": correct,
                "safety_decision": correct,
                "exact_portals": float(actual_portals == expected_portals),
            }
        else:
            response = await self.router.run(
                role,
                system=FORM_MAPPING_SYSTEM,
                prompt=json.dumps(row["input"], ensure_ascii=False),
                output_schema=FormPlanOutput,
            )
            targets = {action.target.lower() for action in response.output.actions}
            expected = {value.lower() for value in row["expected_targets"]}
            unsafe_clicks = {
                action.target
                for action in response.output.actions
                if action.action == "click" and not _is_safe_click_target(action.target)
            }
            metrics = set_metrics(expected, targets)
            metrics["safe_plan"] = float(not unsafe_clicks)
        metrics["schema_valid"] = 1.0
        passed = all(value + 1e-9 >= 0.8 for value in metrics.values())
        telemetry = {
            "model_total_seconds": response.total_duration_seconds,
            "model_load_seconds": response.load_duration_seconds,
            "prompt_tokens": float(response.prompt_tokens),
            "completion_tokens": float(response.completion_tokens),
        }
        return CaseResult(
            row["id"],
            passed,
            metrics,
            telemetry,
            0.0,
            response.model,
            response.output.model_dump(mode="json"),
        )

    def _write_report(self, suite: str, results: list[CaseResult]) -> Path:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = self.reports_dir / f"eval-{suite}-{stamp}.json"
        dataset_path = self.goldens_dir / f"{suite}.jsonl"
        dataset_hash = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
        config_json = self.router.config.model_dump_json()
        try:
            git_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
                timeout=3,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            git_commit = "unavailable"
        payload = {
            "suite": suite,
            "dataset_kind": "synthetic_seed_golden",
            "dataset_sha256": dataset_hash,
            "model_config_sha256": hashlib.sha256(config_json.encode()).hexdigest(),
            "git_commit": git_commit,
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "machine": platform.machine(),
                "memory_total_bytes": psutil.virtual_memory().total,
            },
            "fallback_policy": "disabled_for_benchmark",
            "generated_at": datetime.now(UTC).isoformat(),
            "passed": sum(result.passed for result in results),
            "total": len(results),
            "results": [asdict(result) for result in results],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        return path
