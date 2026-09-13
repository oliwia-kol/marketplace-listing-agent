from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from marketplace_agent.domain.models import ItemCase, PortalDraft

SCHEMA_VERSION = 3


@contextmanager
def _connection(path: Path) -> Iterator[sqlite3.Connection]:
    """Commit or roll back like sqlite3's context manager, then always close."""
    connection = sqlite3.connect(path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _file_record(path: Path, index: int) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "index": index,
        "file_name": path.name,
        "size_bytes": len(content),
        "sha256": _sha256_bytes(content),
    }


class CatalogRepository:
    """Small explicit repository: domain data stays separate from LangGraph checkpoints."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def setup(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with _connection(self.database_path) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=5000")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS item_cases (
                    item_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversation_notes (
                    channel_id TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(channel_id, item_id)
                );
                CREATE TABLE IF NOT EXISTS listing_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    portal TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(item_id, portal, version),
                    UNIQUE(item_id, portal, content_hash)
                );
                CREATE TABLE IF NOT EXISTS approval_records (
                    approval_id TEXT PRIMARY KEY,
                    token TEXT NOT NULL UNIQUE,
                    channel_id TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    step TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    snapshot_ids_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    consumed_at TEXT
                );
                CREATE INDEX IF NOT EXISTS approval_pending_idx
                    ON approval_records(channel_id, item_id, status, created_at);
                CREATE TABLE IF NOT EXISTS execution_jobs (
                    job_id TEXT PRIMARY KEY,
                    approval_id TEXT NOT NULL UNIQUE,
                    snapshot_id TEXT NOT NULL,
                    portal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    attempt INTEGER NOT NULL DEFAULT 0,
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS intervention_requests (
                    intervention_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    instruction TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT
                );
                CREATE TABLE IF NOT EXISTS conversation_events (
                    event_id TEXT PRIMARY KEY,
                    channel_id TEXT NOT NULL,
                    item_id TEXT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS run_events (
                    event_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    item_id TEXT,
                    component TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            job_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(execution_jobs)")
            }
            for name, declaration in {
                "locked_by": "TEXT",
                "locked_at": "TEXT",
                "publish_approval_id": "TEXT",
            }.items():
                if name not in job_columns:
                    connection.execute(
                        f"ALTER TABLE execution_jobs ADD COLUMN {name} {declaration}"
                    )
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, datetime.now(UTC).isoformat()),
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS preferences (
                    preference_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    kind TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_sessions (
                    channel_id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def save_item(self, item: ItemCase) -> None:
        item.updated_at = datetime.now(UTC)
        payload = item.model_dump_json()
        with _connection(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO item_cases (item_id, status, payload_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                    status=excluded.status,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (item.item_id, item.status.value, payload, item.updated_at.isoformat()),
            )

    def get_item(self, item_id: str) -> ItemCase | None:
        with _connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT payload_json FROM item_cases WHERE item_id = ?", (item_id,)
            ).fetchone()
        return ItemCase.model_validate_json(row[0]) if row else None

    def save_preference(self, kind: str, value: dict, category: str | None = None) -> None:
        with _connection(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO preferences (category, kind, value_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    category,
                    kind,
                    json.dumps(value, ensure_ascii=False),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def list_preferences(self, category: str | None = None) -> list[dict]:
        with _connection(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT category, kind, value_json, created_at
                FROM preferences
                WHERE category IS NULL OR category = ?
                ORDER BY preference_id DESC
                """,
                (category,),
            ).fetchall()
        return [
            {
                "category": row[0],
                "kind": row[1],
                "value": json.loads(row[2]),
                "created_at": row[3],
            }
            for row in rows
        ]

    def set_active_item(self, channel_id: str, item_id: str) -> None:
        with _connection(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO channel_sessions (channel_id, item_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    item_id=excluded.item_id,
                    updated_at=excluded.updated_at
                """,
                (channel_id, item_id, datetime.now(UTC).isoformat()),
            )

    def get_active_item(self, channel_id: str) -> str | None:
        with _connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT item_id FROM channel_sessions WHERE channel_id = ?", (channel_id,)
            ).fetchone()
        return str(row[0]) if row else None

    def clear_active_item(self, channel_id: str) -> None:
        with _connection(self.database_path) as connection:
            connection.execute("DELETE FROM channel_sessions WHERE channel_id = ?", (channel_id,))

    def append_note(self, channel_id: str, item_id: str, text: str) -> None:
        clean = text.strip()
        if not clean:
            return
        with _connection(self.database_path) as connection:
            current = connection.execute(
                "SELECT notes FROM conversation_notes WHERE channel_id = ? AND item_id = ?",
                (channel_id, item_id),
            ).fetchone()
            notes = "\n".join(part for part in [current[0] if current else "", clean] if part)
            connection.execute(
                """
                INSERT INTO conversation_notes(channel_id, item_id, notes, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(channel_id, item_id) DO UPDATE SET
                    notes=excluded.notes, updated_at=excluded.updated_at
                """,
                (channel_id, item_id, notes, datetime.now(UTC).isoformat()),
            )

    def get_notes(self, channel_id: str, item_id: str) -> str:
        with _connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT notes FROM conversation_notes WHERE channel_id = ? AND item_id = ?",
                (channel_id, item_id),
            ).fetchone()
        return str(row[0]) if row else ""

    def create_listing_snapshot(self, item: ItemCase, draft: PortalDraft) -> str:
        photos = [_file_record(path, index) for index, path in enumerate(item.photo_paths)]
        payload = {
            "item_id": item.item_id,
            "portal": draft.portal,
            "facts": item.facts.approved_dict(),
            "draft": draft.model_dump(mode="json"),
            "photos": photos,
            "pricing_evidence": (
                item.price_summary.evidence_manifest_path if item.price_summary else None
            ),
        }
        payload_json = _canonical_json(payload)
        content_hash = _sha256_bytes(payload_json.encode())
        now = datetime.now(UTC).isoformat()
        with _connection(self.database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT snapshot_id FROM listing_snapshots
                WHERE item_id = ? AND portal = ? AND content_hash = ?
                """,
                (item.item_id, draft.portal, content_hash),
            ).fetchone()
            if existing:
                return str(existing[0])
            row = connection.execute(
                """
                SELECT COALESCE(MAX(version), 0)
                FROM listing_snapshots WHERE item_id = ? AND portal = ?
                """,
                (item.item_id, draft.portal),
            ).fetchone()
            version = int(row[0]) + 1
            snapshot_id = uuid4().hex
            connection.execute(
                """
                INSERT INTO listing_snapshots(
                    snapshot_id, item_id, version, portal, payload_json, content_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (snapshot_id, item.item_id, version, draft.portal, payload_json, content_hash, now),
            )
            connection.execute(
                """
                UPDATE approval_records SET status = 'revoked'
                WHERE item_id = ? AND status = 'pending'
                """,
                (item.item_id,),
            )
        return snapshot_id

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        with _connection(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT snapshot_id, item_id, version, portal, payload_json, content_hash, created_at
                FROM listing_snapshots WHERE snapshot_id = ?
                """,
                (snapshot_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "snapshot_id": row[0],
            "item_id": row[1],
            "version": row[2],
            "portal": row[3],
            "payload": json.loads(row[4]),
            "content_hash": row[5],
            "created_at": row[6],
        }

    def issue_approval(
        self,
        *,
        channel_id: str,
        item_id: str,
        step: str,
        payload: dict[str, Any],
        snapshot_ids: list[str] | None = None,
        ttl_hours: int = 24,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        approval_id = uuid4().hex
        token = secrets.token_urlsafe(9)
        payload_json = _canonical_json(payload)
        payload_hash = _sha256_bytes(payload_json.encode())
        snapshots = sorted(snapshot_ids or [])
        with _connection(self.database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                UPDATE approval_records SET status = 'revoked'
                WHERE channel_id = ? AND item_id = ? AND status = 'pending'
                """,
                (channel_id, item_id),
            )
            connection.execute(
                """
                INSERT INTO approval_records(
                    approval_id, token, channel_id, item_id, step, payload_hash,
                    payload_json, snapshot_ids_json, status, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    approval_id,
                    token,
                    channel_id,
                    item_id,
                    step,
                    payload_hash,
                    payload_json,
                    _canonical_json(snapshots),
                    now.isoformat(),
                    (now + timedelta(hours=ttl_hours)).isoformat(),
                ),
            )
        return {
            "approval_id": approval_id,
            "token": token,
            "payload_hash": payload_hash,
            "snapshot_ids": snapshots,
            "step": step,
            "payload": payload,
        }

    def pending_approval(self, channel_id: str, item_id: str) -> dict[str, Any] | None:
        with _connection(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT approval_id, token, step, payload_json, snapshot_ids_json, expires_at
                FROM approval_records
                WHERE channel_id = ? AND item_id = ? AND status = 'pending'
                ORDER BY created_at DESC LIMIT 1
                """,
                (channel_id, item_id),
            ).fetchone()
        if row is None:
            return None
        return {
            "approval_id": row[0],
            "token": row[1],
            "step": row[2],
            "payload": json.loads(row[3]),
            "snapshot_ids": json.loads(row[4]),
            "expires_at": row[5],
        }

    def consume_approval(
        self, *, token: str, channel_id: str, item_id: str, expected_step: str
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        with _connection(self.database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT approval_id, step, payload_json, snapshot_ids_json, status, expires_at
                FROM approval_records
                WHERE token = ? AND channel_id = ? AND item_id = ?
                """,
                (token, channel_id, item_id),
            ).fetchone()
            if row is None:
                raise PermissionError("approval not found for this user and item")
            if row[4] != "pending":
                raise PermissionError(f"approval is {row[4]}")
            if row[1] != expected_step:
                raise PermissionError("approval belongs to a different workflow step")
            if datetime.fromisoformat(row[5]) <= now:
                connection.execute(
                    "UPDATE approval_records SET status = 'expired' WHERE approval_id = ?",
                    (row[0],),
                )
                raise PermissionError("approval expired")
            changed = connection.execute(
                """
                UPDATE approval_records SET status = 'consumed', consumed_at = ?
                WHERE approval_id = ? AND status = 'pending'
                """,
                (now.isoformat(), row[0]),
            ).rowcount
            if changed != 1:
                raise PermissionError("approval was already consumed")
        return {
            "approval_id": row[0],
            "step": row[1],
            "payload": json.loads(row[2]),
            "snapshot_ids": json.loads(row[3]),
        }

    def revoke_pending_approval(self, channel_id: str, item_id: str) -> None:
        with _connection(self.database_path) as connection:
            connection.execute(
                """
                UPDATE approval_records SET status = 'revoked'
                WHERE channel_id = ? AND item_id = ? AND status = 'pending'
                """,
                (channel_id, item_id),
            )

    def validate_consumed_approval(
        self, approval_id: str, item_id: str, step: str, snapshot_ids: list[str]
    ) -> bool:
        with _connection(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT status, item_id, step, snapshot_ids_json
                FROM approval_records WHERE approval_id = ?
                """,
                (approval_id,),
            ).fetchone()
        return bool(
            row
            and row[0] == "consumed"
            and row[1] == item_id
            and row[2] == step
            and json.loads(row[3]) == sorted(snapshot_ids)
        )

    def is_snapshot_approved(self, snapshot_id: str) -> bool:
        with _connection(self.database_path) as connection:
            rows = connection.execute(
                """SELECT snapshot_ids_json FROM approval_records
                   WHERE status='consumed' AND step='fill_authorization'"""
            ).fetchall()
        return any(snapshot_id in json.loads(row[0]) for row in rows)

    def record_conversation_event(
        self, channel_id: str, item_id: str | None, event_type: str, payload: dict[str, Any]
    ) -> None:
        with _connection(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO conversation_events(
                    event_id, channel_id, item_id, event_type, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid4().hex,
                    channel_id,
                    item_id,
                    event_type,
                    _canonical_json(payload),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def record_run_event(
        self,
        run_id: str,
        item_id: str | None,
        component: str,
        operation: str,
        status: str,
        payload: dict[str, Any],
    ) -> None:
        with _connection(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO run_events(
                    event_id, run_id, item_id, component, operation,
                    status, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid4().hex,
                    run_id,
                    item_id,
                    component,
                    operation,
                    status,
                    _canonical_json(payload),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def list_run_events(self, run_id: str | None = None) -> list[dict[str, Any]]:
        with _connection(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT event_id, run_id, item_id, component, operation,
                       status, payload_json, created_at
                FROM run_events
                WHERE ? IS NULL OR run_id = ?
                ORDER BY created_at, event_id
                """,
                (run_id, run_id),
            ).fetchall()
        return [
            {
                "event_id": row[0],
                "run_id": row[1],
                "item_id": row[2],
                "component": row[3],
                "operation": row[4],
                "status": row[5],
                "payload": json.loads(row[6]),
                "created_at": row[7],
            }
            for row in rows
        ]

    def enqueue_execution(
        self, *, approval_id: str, snapshot_id: str, portal: str
    ) -> dict[str, Any]:
        snapshot = self.get_snapshot(snapshot_id)
        if snapshot is None or snapshot["portal"] != portal:
            raise ValueError("snapshot does not belong to this portal")
        if not self.validate_consumed_approval(
            approval_id, snapshot["item_id"], "fill_authorization", [snapshot_id]
        ):
            # A multi-portal approval contains more than one snapshot. Check membership
            # without accepting a snapshot that was never shown to the user.
            with _connection(self.database_path) as connection:
                approval = connection.execute(
                    """SELECT status, item_id, step, snapshot_ids_json
                    FROM approval_records WHERE approval_id = ?""",
                    (approval_id,),
                ).fetchone()
            if not (
                approval
                and approval[0] == "consumed"
                and approval[1] == snapshot["item_id"]
                and approval[2] == "fill_authorization"
                and snapshot_id in json.loads(approval[3])
            ):
                raise PermissionError("approval is not bound to this snapshot")
        idempotency_key = _sha256_bytes(f"fill:{snapshot_id}:{approval_id}".encode())
        now = datetime.now(UTC).isoformat()
        with _connection(self.database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT job_id FROM execution_jobs WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if existing:
                return self.get_execution_job(str(existing[0]))
            job_id = uuid4().hex
            connection.execute(
                """INSERT INTO execution_jobs(
                    job_id, approval_id, snapshot_id, portal, status, idempotency_key,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'queued', ?, ?, ?)""",
                (job_id, approval_id, snapshot_id, portal, idempotency_key, now, now),
            )
        return self.get_execution_job(job_id)

    def get_execution_job(self, job_id: str) -> dict[str, Any] | None:
        with _connection(self.database_path) as connection:
            row = connection.execute(
                """SELECT job_id, approval_id, snapshot_id, portal, status,
                          idempotency_key, attempt, result_json, created_at, updated_at,
                          locked_by, locked_at, publish_approval_id
                   FROM execution_jobs WHERE job_id = ?""",
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        keys = (
            "job_id",
            "approval_id",
            "snapshot_id",
            "portal",
            "status",
            "idempotency_key",
            "attempt",
            "result",
            "created_at",
            "updated_at",
            "locked_by",
            "locked_at",
            "publish_approval_id",
        )
        values = list(row)
        values[7] = json.loads(values[7]) if values[7] else None
        return dict(zip(keys, values, strict=True))

    def list_execution_jobs(self, item_id: str | None = None) -> list[dict[str, Any]]:
        with _connection(self.database_path) as connection:
            rows = connection.execute(
                """SELECT execution_jobs.job_id
                   FROM execution_jobs
                   JOIN listing_snapshots
                     ON listing_snapshots.snapshot_id = execution_jobs.snapshot_id
                   WHERE ? IS NULL OR listing_snapshots.item_id = ?
                   ORDER BY execution_jobs.created_at""",
                (item_id, item_id),
            ).fetchall()
        return [job for row in rows if (job := self.get_execution_job(str(row[0]))) is not None]

    def claim_next_execution(self, worker_id: str) -> dict[str, Any] | None:
        now = datetime.now(UTC).isoformat()
        with _connection(self.database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT job_id, status FROM execution_jobs
                   WHERE status IN ('queued', 'authorized_to_publish')
                   ORDER BY created_at LIMIT 1"""
            ).fetchone()
            if row is None:
                return None
            target_status = "preparing" if row[1] == "queued" else "submitting"
            changed = connection.execute(
                """UPDATE execution_jobs SET status=?, attempt=attempt+1,
                          locked_by=?, locked_at=?, updated_at=?
                   WHERE job_id=? AND status=?""",
                (target_status, worker_id, now, now, row[0], row[1]),
            ).rowcount
            if changed != 1:
                return None
        job = self.get_execution_job(str(row[0]))
        if job is not None:
            job["operation"] = "prepare" if row[1] == "queued" else "publish"
        return job

    def recover_stale_executions(self, stale_after_seconds: int = 900) -> dict[str, int]:
        """Recover an abandoned worker lease without risking a duplicate submit.

        Preparation is reversible, so it can return to the queue. A submit may
        already have reached the portal, so an abandoned submit becomes
        ``unknown`` and must be reconciled by observation instead of retried.
        """
        cutoff = (datetime.now(UTC) - timedelta(seconds=stale_after_seconds)).isoformat()
        now = datetime.now(UTC).isoformat()
        with _connection(self.database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            preparing = connection.execute(
                """UPDATE execution_jobs
                   SET status='queued', result_json=?, locked_by=NULL, locked_at=NULL,
                       updated_at=?
                   WHERE status='preparing' AND locked_at IS NOT NULL AND locked_at < ?""",
                (_canonical_json({"reason": "stale_prepare_requeued"}), now, cutoff),
            ).rowcount
            submitting = connection.execute(
                """UPDATE execution_jobs
                   SET status='unknown', result_json=?, locked_by=NULL, locked_at=NULL,
                       updated_at=?
                   WHERE status='submitting' AND locked_at IS NOT NULL AND locked_at < ?""",
                (
                    _canonical_json({"reason": "stale_submit_requires_reconciliation"}),
                    now,
                    cutoff,
                ),
            ).rowcount
        return {"requeued_prepare": int(preparing), "unknown_submit": int(submitting)}

    def attach_publish_approval(self, job_id: str, approval_id: str) -> None:
        job = self.get_execution_job(job_id)
        if job is None:
            raise KeyError(job_id)
        snapshot = self.get_snapshot(job["snapshot_id"])
        assert snapshot is not None
        if not self.validate_consumed_approval(
            approval_id,
            snapshot["item_id"],
            "publish_authorization",
            [job["snapshot_id"]],
        ):
            raise PermissionError("publish approval is not bound to this job snapshot")
        if job["status"] != "ready":
            raise PermissionError("only a readback-ready job can be published")
        with _connection(self.database_path) as connection:
            connection.execute(
                """UPDATE execution_jobs SET publish_approval_id=?,
                          status='authorized_to_publish', updated_at=? WHERE job_id=?""",
                (approval_id, datetime.now(UTC).isoformat(), job_id),
            )

    def set_execution_status(
        self, job_id: str, status: str, result: dict[str, Any] | None = None
    ) -> None:
        allowed = {
            "queued",
            "preparing",
            "ready",
            "waiting_user",
            "submitting",
            "published",
            "pending_moderation",
            "failed",
            "unknown",
            "cancelled",
            "authorized_to_publish",
        }
        if status not in allowed:
            raise ValueError(f"unsupported execution status: {status}")
        with _connection(self.database_path) as connection:
            changed = connection.execute(
                """UPDATE execution_jobs SET status=?, result_json=?, updated_at=?,
                          locked_by=NULL, locked_at=NULL
                   WHERE job_id=?""",
                (
                    status,
                    _canonical_json(result) if result is not None else None,
                    datetime.now(UTC).isoformat(),
                    job_id,
                ),
            ).rowcount
        if changed != 1:
            raise KeyError(job_id)

    def create_intervention(
        self, *, job_id: str, kind: str, instruction: str, state: dict[str, Any]
    ) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        with _connection(self.database_path) as connection:
            existing = connection.execute(
                """SELECT intervention_id FROM intervention_requests
                   WHERE job_id=? AND kind=? AND status='open'""",
                (job_id, kind),
            ).fetchone()
            if existing:
                return self.get_intervention(str(existing[0]))
            intervention_id = uuid4().hex
            connection.execute(
                """INSERT INTO intervention_requests(
                    intervention_id, job_id, kind, instruction, state_json,
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, 'open', ?)""",
                (intervention_id, job_id, kind, instruction, _canonical_json(state), now),
            )
        self.set_execution_status(job_id, "waiting_user", {"intervention_id": intervention_id})
        return self.get_intervention(intervention_id)

    def get_intervention(self, intervention_id: str) -> dict[str, Any] | None:
        with _connection(self.database_path) as connection:
            row = connection.execute(
                """SELECT intervention_id, job_id, kind, instruction, state_json,
                          status, created_at, resolved_at
                   FROM intervention_requests WHERE intervention_id=?""",
                (intervention_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "intervention_id": row[0],
            "job_id": row[1],
            "kind": row[2],
            "instruction": row[3],
            "state": json.loads(row[4]),
            "status": row[5],
            "created_at": row[6],
            "resolved_at": row[7],
        }

    def resume_intervention(self, job_id: str, intervention_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        with _connection(self.database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                """UPDATE intervention_requests SET status='resumed', resolved_at=?
                   WHERE intervention_id=? AND job_id=? AND status='open'""",
                (now, intervention_id, job_id),
            ).rowcount
            if changed != 1:
                raise PermissionError("intervention is not open for this job")
            connection.execute(
                """UPDATE execution_jobs SET status='queued', updated_at=? WHERE job_id=?""",
                (now, job_id),
            )

    def cancel_execution(self, job_id: str) -> None:
        self.set_execution_status(job_id, "cancelled", {"reason": "user_requested"})

    def emergency_stop(self) -> int:
        with _connection(self.database_path) as connection:
            changed = connection.execute(
                """UPDATE execution_jobs SET status='cancelled', result_json=?, updated_at=?
                   WHERE status IN ('queued','preparing','waiting_user')""",
                (_canonical_json({"reason": "emergency_stop"}), datetime.now(UTC).isoformat()),
            ).rowcount
        return int(changed)
