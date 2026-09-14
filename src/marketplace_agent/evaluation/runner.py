from __future__ import annotations

import hashlib
import json
import math
import platform
import statistics
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

from marketplace_agent.browser.forms import FORM_MAPPING_SYSTEM, _is_safe_click_target
from marketplace_agent.domain.copy_pipeline import (
    assess_draft,
    build_copy_brief,
    portal_draft_from_text,
)
from marketplace_agent.domain.models import ComparableCandidate, FactProposal
from marketplace_agent.domain.pricing import summarize_prices
from marketplace_agent.evaluation.metrics import classification_metrics, set_metrics
from marketplace_agent.models.router import ModelRole, ModelRouter
from marketplace_agent.models.tasks import (
    ComparableAuditOutput,
    CopyAuditOutput,
    CopyTextOutput,
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
        self._effective_config_json: str | None = None
        self._evaluation_scope: dict[str, Any] = {}
        self._dataset_kind = "synthetic_seed_golden"

    async def run(
        self,
        suite: str,
        model_override: str | None = None,
        *,
        repeats: int = 1,
        generation_overrides: dict[str, Any] | None = None,
        split: str | None = None,
        limit: int | None = None,
        case_ids: set[str] | None = None,
    ) -> Path:
        self._effective_config_json = None
        self._evaluation_scope = {
            "split": split,
            "limit": limit,
            "case_ids": sorted(case_ids) if case_ids else None,
            "repeats": repeats,
            "generation_overrides": generation_overrides or {},
        }
        if suite == "price_math":
            results = self._price_math()
        elif suite in {
            "facts",
            "comparables",
            "copy",
            "copy_quality",
            "copy_real_anonymized",
            "copy_audit",
            "copy_audit_mutations",
            "forms",
        }:
            results = await self._model_suite(
                suite,
                model_override,
                repeats=repeats,
                generation_overrides=generation_overrides or {},
                split=split,
                limit=limit,
                case_ids=case_ids,
            )
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

    async def _model_suite(
        self,
        suite: str,
        model_override: str | None,
        *,
        repeats: int,
        generation_overrides: dict[str, Any],
        split: str | None,
        limit: int | None,
        case_ids: set[str] | None,
    ) -> list[CaseResult]:
        if repeats < 1 or repeats > 10:
            raise ValueError("repeats must be between 1 and 10")
        path = self.goldens_dir / f"{suite}.jsonl"
        results: list[CaseResult] = []
        role = {
            "facts": ModelRole.VISION_FAST,
            "comparables": ModelRole.MARKET_EXPERT,
            "copy": ModelRole.POLISH_COPYWRITER,
            "copy_quality": ModelRole.POLISH_COPYWRITER,
            "copy_real_anonymized": ModelRole.POLISH_COPYWRITER,
            "copy_audit": ModelRole.MARKET_EXPERT,
            "copy_audit_mutations": ModelRole.MARKET_EXPERT,
            "forms": ModelRole.GUI_FALLBACK,
        }[suite]
        original_config = self.router.config.roles[role].model_copy(deep=True)
        if model_override:
            self.router.config.roles[role].model = model_override
        # Benchmarks must measure the selected model. A silent fallback would make
        # two runs incomparable while still looking successful.
        self.router.config.roles[role].fallback = None
        for name, value in generation_overrides.items():
            if value is not None:
                setattr(self.router.config.roles[role], name, value)
        rows = load_jsonl(path)
        if split:
            rows = [row for row in rows if row.get("split") == split]
        if case_ids:
            known_ids = {row["id"] for row in rows}
            missing_ids = case_ids - known_ids
            if missing_ids:
                raise ValueError(f"Unknown case ids: {sorted(missing_ids)}")
            rows = [row for row in rows if row["id"] in case_ids]
        if limit is not None:
            if limit < 1:
                raise ValueError("limit must be positive")
            rows = rows[:limit]
        if not rows:
            raise ValueError(f"No cases selected for suite={suite}, split={split!r}")
        provenance = {row.get("provenance") for row in rows}
        self._dataset_kind = provenance.pop() if len(provenance) == 1 else "mixed_provenance"
        self._effective_config_json = self.router.config.model_dump_json()
        self._evaluation_scope.update(
            {
                "role": role.value,
                "selected_case_count": len(rows),
                "effective_role_config": self.router.config.roles[role].model_dump(mode="json"),
            }
        )
        try:
            for repeat_index in range(repeats):
                for row in rows:
                    started = time.perf_counter()
                    memory_before = psutil.Process().memory_info().rss
                    try:
                        result = await self._run_case(suite, role, row)
                        if repeats > 1:
                            result.case_id = f"{result.case_id}#run-{repeat_index + 1}"
                        result.latency_seconds = time.perf_counter() - started
                        result.telemetry["python_rss_delta_mb"] = (
                            psutil.Process().memory_info().rss - memory_before
                        ) / 1_048_576
                    except Exception as error:
                        case_id = row["id"]
                        if repeats > 1:
                            case_id = f"{case_id}#run-{repeat_index + 1}"
                        result = CaseResult(
                            case_id=case_id,
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
            self.router.config.roles[role] = original_config
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
        elif suite in {"copy", "copy_quality", "copy_real_anonymized"}:
            facts = row["input"]["facts"]
            proposals = [
                FactProposal(
                    name=name,
                    value=value,
                    confidence=1,
                    source="user",
                    approved=True,
                )
                for name, value in facts.items()
            ]
            proposals.extend(
                FactProposal(
                    name=spec["name"],
                    value=spec["value"],
                    confidence=1,
                    source="manufacturer",
                    scope="product_spec",
                    source_url=spec["source_url"],
                    source_excerpt=spec.get("source_excerpt"),
                    approved=True,
                )
                for spec in row["input"].get("product_specs", [])
            )
            brief = build_copy_brief(
                proposals,
                row["input"]["portals"],
                row["input"].get("preferences", []),
            )
            response = await self.router.run(
                role,
                system=COPY_SYSTEM,
                prompt=brief.model_dump_json(),
                output_schema=CopyTextOutput,
            )
            drafts = [
                portal_draft_from_text(
                    value,
                    facts=facts,
                    price_pln=float(row["input"]["price_pln"]),
                )
                for value in response.output.drafts
            ]
            text = " ".join(f"{draft.title} {draft.description}" for draft in drafts).lower()
            forbidden = [value.lower() for value in row["forbidden_phrases"]]
            assessments = [assess_draft(draft, brief) for draft in drafts]
            required_count = sum(claim.required for claim in brief.claims) * len(drafts)
            missing_count = sum(len(result.missing_required_keys) for result in assessments)
            expected_portals = set(row["input"]["portals"])
            metrics = {
                "required_fact_recall": (
                    1 - missing_count / required_count if required_count else 1.0
                ),
                "hallucination_guard": float(
                    not any(value in text for value in forbidden)
                    and not any(result.unsupported_claims for result in assessments)
                ),
                "exact_portals": float({draft.portal for draft in drafts} == expected_portals),
            }
        elif suite in {"copy_audit", "copy_audit_mutations"}:
            facts = row["input"]["facts"]
            brief = build_copy_brief(
                [
                    FactProposal(
                        name=name,
                        value=value,
                        confidence=1,
                        source="user",
                        approved=True,
                    )
                    for name, value in facts.items()
                ],
                [draft["portal"] for draft in row["input"]["drafts"]],
            )
            response = await self.router.run(
                role,
                system=COPY_AUDIT_SYSTEM,
                prompt=json.dumps(
                    {"brief": brief.model_dump(mode="json"), "drafts": row["input"]["drafts"]},
                    ensure_ascii=False,
                ),
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
        config_json = self._effective_config_json or self.router.config.model_dump_json()
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
        metric_names = sorted({name for result in results for name in result.metrics})
        aggregate_metrics = {
            name: statistics.fmean(result.metrics.get(name, 0.0) for result in results)
            for name in metric_names
        }
        latencies = [result.latency_seconds for result in results]
        sorted_latencies = sorted(latencies)
        p95_index = max(0, math.ceil(0.95 * len(sorted_latencies)) - 1)
        payload = {
            "suite": suite,
            "dataset_kind": self._dataset_kind,
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
            "evaluation_scope": self._evaluation_scope,
            "generated_at": datetime.now(UTC).isoformat(),
            "passed": sum(result.passed for result in results),
            "total": len(results),
            "pass_rate": sum(result.passed for result in results) / len(results),
            "aggregate_metrics": aggregate_metrics,
            "latency_seconds": {
                "mean": statistics.fmean(latencies),
                "p95": sorted_latencies[p95_index],
                "max": max(latencies),
            },
            "results": [asdict(result) for result in results],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        return path
