from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path


def backup_sqlite(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with closing(sqlite3.connect(source)) as source_db, closing(
        sqlite3.connect(destination)
    ) as target_db:
        source_db.backup(target_db)
    destination.chmod(0o600)


def create_backup(catalog_db: Path, checkpoint_db: Path, destination_root: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = destination_root / f"backup-{stamp}"
    destination.mkdir(parents=True, mode=0o700)
    files = []
    for source in (catalog_db, checkpoint_db):
        if source.exists():
            target = destination / source.name
            backup_sqlite(source, target)
            files.append(source.name)
    manifest = destination / "manifest.json"
    manifest.write_text(
        json.dumps({"created_at": datetime.now(UTC).isoformat(), "files": files}, indent=2),
        encoding="utf-8",
    )
    manifest.chmod(0o600)
    return destination


def restore_backup(source_dir: Path, destination_data_dir: Path) -> list[Path]:
    if destination_data_dir.exists() and any(destination_data_dir.iterdir()):
        raise FileExistsError("restore destination must be empty or absent")
    manifest = json.loads((source_dir / "manifest.json").read_text(encoding="utf-8"))
    destination_data_dir.mkdir(parents=True, mode=0o700)
    restored = []
    for name in manifest["files"]:
        source = source_dir / Path(name).name
        target = destination_data_dir / Path(name).name
        backup_sqlite(source, target)
        restored.append(target)
    return restored
