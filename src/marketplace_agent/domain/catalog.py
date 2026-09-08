from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from marketplace_agent.domain.models import ItemCase


class CatalogRepository:
    """Small explicit repository: domain data stays separate from LangGraph checkpoints."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def setup(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as connection:
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
        with sqlite3.connect(self.database_path) as connection:
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
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT payload_json FROM item_cases WHERE item_id = ?", (item_id,)
            ).fetchone()
        return ItemCase.model_validate_json(row[0]) if row else None

    def save_preference(self, kind: str, value: dict, category: str | None = None) -> None:
        with sqlite3.connect(self.database_path) as connection:
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
        with sqlite3.connect(self.database_path) as connection:
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
        with sqlite3.connect(self.database_path) as connection:
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
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT item_id FROM channel_sessions WHERE channel_id = ?", (channel_id,)
            ).fetchone()
        return str(row[0]) if row else None

    def clear_active_item(self, channel_id: str) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("DELETE FROM channel_sessions WHERE channel_id = ?", (channel_id,))
