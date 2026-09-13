# ADR 0009: retain LoRA as an experiment, not the default copywriter

Status: accepted, 2026-09-13.

Qwen3-0.6B was trained with LoRA on 240 synthetic examples and evaluated on 30 held-out
family-level examples. The adapter corrected the base model's JSON-echo behavior and
matched all literal test targets, but a deterministic template achieved the same narrow
result with lower cost and stronger guarantees.

The adapter remains a reproducible local artifact. Product integration requires diverse,
approved, anonymized real examples and a stronger semantic hallucination evaluation.
