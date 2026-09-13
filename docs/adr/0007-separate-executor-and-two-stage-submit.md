# ADR 0007: separate executor and two-stage publication approval

Status: accepted, 2026-09-13.

The orchestrator writes idempotent jobs. A separate worker owns the persistent sales
profile and accepts only a `job_id`; it reloads the immutable snapshot from SQLite.
Form preparation and portal submission are separate phases. Submission requires a
second approval after successful readback and an additional readback immediately before
the exact allow-listed button click.

CAPTCHA, login, fees, unknown controls and manual differences create durable intervention
records. A post-submit timeout produces `unknown`; reconciliation reads state without
clicking again. Live submit is disabled by default.
