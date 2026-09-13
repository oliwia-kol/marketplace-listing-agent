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
    backup = create_backup(catalog, data / "checkpoints.sqlite", tmp_path / "backups")
    restored = restore_backup(backup, tmp_path / "restored")
    with closing(sqlite3.connect(restored[0])) as connection:
        assert connection.execute("SELECT value FROM sample").fetchone()[0] == "ok"


def test_restore_refuses_non_empty_destination(tmp_path) -> None:
    source = tmp_path / "backup"
    source.mkdir()
    (source / "manifest.json").write_text('{"files": []}')
    destination = tmp_path / "existing"
    destination.mkdir()
    (destination / "keep.txt").write_text("keep")
    with pytest.raises(FileExistsError):
        restore_backup(source, destination)
