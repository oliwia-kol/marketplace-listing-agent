import sqlite3
from contextlib import closing

import pytest

from marketplace_agent.operations.backup import create_backup, restore_backup


def test_backup_and_restore_to_new_directory(tmp_path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    catalog = data / "catalog.sqlite"
    with closing(sqlite3.connect(catalog)) as connection:
        connection.execute("CREATE TABLE sample(value TEXT)")
        connection.execute("INSERT INTO sample VALUES ('ok')")
        connection.commit()
    photo = data / "items" / "item-1" / "photos" / "01.jpg"
    photo.parent.mkdir(parents=True)
    photo.write_bytes(b"photo")
    config = tmp_path / "models.yaml"
    config.write_text("roles: {}")
    backup = create_backup(
        catalog,
        data / "checkpoints.sqlite",
        tmp_path / "backups",
        data_dir=data,
        config_paths=(config,),
    )
    restored = restore_backup(backup, tmp_path / "restored")
    with closing(sqlite3.connect(tmp_path / "restored" / "data" / "catalog.sqlite")) as connection:
        assert connection.execute("SELECT value FROM sample").fetchone()[0] == "ok"
    restored_photo = tmp_path / "restored" / "data" / "items" / "item-1" / "photos" / "01.jpg"
    assert restored_photo.read_bytes() == b"photo"
    assert (tmp_path / "restored" / "config" / "models.yaml").read_text() == "roles: {}"
    assert set(restored) == {
        tmp_path / "restored" / "data" / "catalog.sqlite",
        restored_photo,
        tmp_path / "restored" / "config" / "models.yaml",
    }


def test_restore_refuses_non_empty_destination(tmp_path) -> None:
    source = tmp_path / "backup"
    source.mkdir()
    (source / "manifest.json").write_text('{"files": []}')
    destination = tmp_path / "existing"
    destination.mkdir()
    (destination / "keep.txt").write_text("keep")
    with pytest.raises(FileExistsError):
        restore_backup(source, destination)


def test_restore_rejects_tampered_file(tmp_path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    catalog = data / "catalog.sqlite"
    with closing(sqlite3.connect(catalog)) as connection:
        connection.execute("CREATE TABLE sample(value TEXT)")
    backup = create_backup(catalog, data / "checkpoints.sqlite", tmp_path / "backups")
    (backup / "data" / "catalog.sqlite").write_bytes(b"tampered")

    with pytest.raises(ValueError, match="checksum mismatch"):
        restore_backup(backup, tmp_path / "restored")

    assert not (tmp_path / "restored").exists()


def test_restore_supports_legacy_flat_sqlite_manifest(tmp_path) -> None:
    backup = tmp_path / "legacy"
    backup.mkdir()
    database = backup / "catalog.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE sample(value TEXT)")
    (backup / "manifest.json").write_text('{"files": ["catalog.sqlite"]}')

    restored = restore_backup(backup, tmp_path / "restored")

    assert restored == [tmp_path / "restored" / "data" / "catalog.sqlite"]
    assert restored[0].is_file()
