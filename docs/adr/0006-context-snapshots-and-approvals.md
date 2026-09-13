# ADR 0006: SQLite is the source of durable context and authority

Status: accepted, 2026-09-13.

LangGraph checkpoints store process position. SQLite domain tables store conversation
notes, item facts, immutable listing snapshots, one-time approvals and execution jobs.
An approval is bound to channel, item, step and the exact set of snapshot IDs. A content
change creates a new snapshot and revokes pending approvals.

This avoids treating model summaries or old checkpoints as facts or authorization.
Transactions with `BEGIN IMMEDIATE` serialize token consumption and job claiming.
