# Portfolio evidence and interview positioning

## Defensible project description

Designed and evaluated a local-first, human-in-the-loop AI system for researching
second-hand prices and preparing Polish marketplace listings. The system uses explicit
LangGraph orchestration, role-based local models, evidence-qualified pricing, immutable
SQLite snapshots, two-stage approvals, guarded browser execution, local observability
and a narrow MCP interface.

Built evaluation and safety layers around the models rather than treating structured
output as factual proof. On 120 synthetic golden cases, deterministic price math and
Qwen comparison/form roles scored 20/20, while the raw Bielik copywriter scored 7/20
and exposed unsupported operability and accessory claims. The production pipeline
therefore combines an independent audit, deterministic claim guards, a safe template
fallback and user approval.

Ran a controlled MLX-LM LoRA experiment on Apple Silicon: 240 train, 30 validation and
30 frozen test examples for Qwen3-0.6B. The adapter fixed a narrow output-format failure,
but tied a deterministic template, so it was documented and deliberately not promoted
to the product without real anonymized data.

## Short CV bullet options

- Designed a local-first LangGraph workflow with SQLite persistence, immutable content
  snapshots, transactional one-time approvals and a separate browser execution worker.
- Built evidence-based marketplace pricing with typed price semantics, multi-channel
  integrity checks, SSRF/DNS defenses and fail-closed exclusion from statistics.
- Evaluated local multimodal and Polish language models on versioned golden datasets;
  implemented grounded-copy auditing and deterministic fallback after measuring model
  hallucinations.
- Implemented local metadata-only observability, GitHub Actions quality gates, MCP v2
  tools, Docker isolation controls and reproducible wheel packaging.
- Trained and evaluated a Qwen3-0.6B LoRA adapter with MLX-LM and rejected deployment
  when a deterministic baseline matched its synthetic frozen-test result.

Use only bullets that match the repository version shown to the interviewer. Describe
the work as AI-assisted engineering and be ready to explain the decisions, tests and
limits in your own words.

## Evidence level today

| Claim | Evidence |
|---|---|
| workflow and persistence work locally | integration tests and SQLite schema |
| safety policy is implemented | targeted regressions and threat model |
| package is installable | clean Python 3.12 wheel smoke test |
| model quality was measured | versioned synthetic datasets and local reports |
| LoRA was actually trained | adapter hash, training history and frozen test |
| CI is configured | checked-in GitHub Actions workflow |
| current logged-in portal works | not yet established |
| real listing was published | not performed |
| Docker image runs on this Mac | build, core doctor and three network-boundary checks |

## Required evidence before publishing the repository

- a privacy and Git-history audit;
- one redacted end-to-end walkthrough without account identifiers;
- a controlled logged-in form inventory for each claimed portal;
- real, anonymized and manually labeled evaluation examples;
- one remote green GitHub Actions run;
- explicit approval for the exact repository state and public wording.

An OLX Partner API adapter should be preferred after OLX approves the application.
Until then, describe the browser path as a guarded local prototype. Allegro Lokalnie
remains browser-based because its official help excludes publication through Allegro API.
