from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_sqlite(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with closing(sqlite3.connect(source)) as source_db, closing(
        sqlite3.connect(destination)
    ) as target_db:
        source_db.backup(target_db)
    destination.chmod(0o600)


def create_backup(
    catalog_db: Path,
    checkpoint_db: Path,
    destination_root: Path,
    *,
    data_dir: Path | None = None,
    config_paths: tuple[Path, ...] = (),
) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = destination_root / f"backup-{stamp}"
    destination.mkdir(parents=True, mode=0o700)
    files: list[dict[str, str]] = []
    for source in (catalog_db, checkpoint_db):
        if source.exists():
            relative = Path("data") / source.name
            target = destination / relative
            backup_sqlite(source, target)
            files.append({"path": relative.as_posix(), "sha256": _sha256(target)})
    source_data_dir = data_dir or catalog_db.parent
    item_root = source_data_dir / "items"
    if item_root.exists():
        for source in sorted(item_root.rglob("*")):
            if source.is_symlink() or not source.is_file():
                continue
            relative = Path("data") / source.relative_to(source_data_dir)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copy2(source, target)
            target.chmod(0o600)
            files.append({"path": relative.as_posix(), "sha256": _sha256(target)})
    for source in config_paths:
        if not source.is_file() or source.is_symlink():
            continue
        relative = Path("config") / source.name
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copy2(source, target)
        target.chmod(0o600)
        files.append({"path": relative.as_posix(), "sha256": _sha256(target)})
    manifest = destination / "manifest.json"
    manifest.write_text(
        json.dumps(
            {"schema_version": 2, "created_at": datetime.now(UTC).isoformat(), "files": files},
            indent=2,
        ),
        encoding="utf-8",
    )
    manifest.chmod(0o600)
    return destination


def restore_backup(source_dir: Path, destination_app_dir: Path) -> list[Path]:
    if destination_app_dir.exists() and any(destination_app_dir.iterdir()):
        raise FileExistsError("restore destination must be empty or absent")
    manifest = json.loads((source_dir / "manifest.json").read_text(encoding="utf-8"))
    source_root = source_dir.resolve()
    validated: list[tuple[Path, Path]] = []
    seen: set[Path] = set()
    for record in manifest["files"]:
        if isinstance(record, str):
            relative = Path("data") / Path(record).name
            source_relative = Path(record).name
            expected_hash = None
        else:
            relative = Path(record["path"])
            source_relative = relative
            expected_hash = record["sha256"]
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not relative.parts
            or relative.parts[0] not in {"data", "config"}
            or relative in seen
        ):
            raise ValueError("backup contains an unsafe path")
        source = source_dir / source_relative
        if (
            source.is_symlink()
            or not source.is_file()
            or not source.resolve().is_relative_to(source_root)
        ):
            raise ValueError(f"backup contains an unsafe file: {relative.as_posix()}")
        if expected_hash and _sha256(source) != expected_hash:
            raise ValueError(f"backup checksum mismatch: {relative.as_posix()}")
        seen.add(relative)
        validated.append((source, relative))

    destination_app_dir.mkdir(parents=True, mode=0o700)
    restored: list[Path] = []
    for source, relative in validated:
        target = destination_app_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if source.suffix == ".sqlite":
            backup_sqlite(source, target)
        else:
            shutil.copy2(source, target)
            target.chmod(0o600)
        restored.append(target)
    return restored
