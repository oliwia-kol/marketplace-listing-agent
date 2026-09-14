from datetime import UTC, datetime, timedelta

import pytest

from marketplace_agent.domain.catalog import CatalogRepository
from marketplace_agent.domain.models import ItemCase, PortalDraft


def test_catalog_roundtrip_and_channel_session(tmp_path) -> None:
    repo = CatalogRepository(tmp_path / "catalog.sqlite")
    repo.setup()
    item = ItemCase()
    repo.save_item(item)
    repo.set_active_item("123", item.item_id)

    restored = repo.get_item(item.item_id)
    assert restored is not None
    assert restored.item_id == item.item_id
    assert repo.get_active_item("123") == item.item_id

    repo.clear_active_item("123")
    assert repo.get_active_item("123") is None


def test_notes_survive_repository_restart(tmp_path) -> None:
    path = tmp_path / "catalog.sqlite"
    repo = CatalogRepository(path)
    repo.setup()
    item = ItemCase()
    repo.save_item(item)
    repo.append_note("chat", item.item_id, "Pierwsza informacja")
    repo.append_note("chat", item.item_id, "Druga informacja")

    reopened = CatalogRepository(path)
    reopened.setup()
    assert reopened.get_notes("chat", item.item_id) == "Pierwsza informacja\nDruga informacja"


def test_snapshot_is_content_addressed_and_detects_changed_photo(tmp_path) -> None:
    repo = CatalogRepository(tmp_path / "catalog.sqlite")
    repo.setup()
    photo = tmp_path / "item.jpg"
    photo.write_bytes(b"first")
    item = ItemCase(photo_paths=[photo])
    draft = PortalDraft(
        portal="olx", title="Konsola", description="Opis", category="Konsole", price_pln=900
    )

    first = repo.create_listing_snapshot(item, draft)
    assert repo.create_listing_snapshot(item, draft) == first
    photo.write_bytes(b"changed")
    second = repo.create_listing_snapshot(item, draft)

    assert second != first
    assert repo.get_snapshot(first)["version"] == 1
    assert repo.get_snapshot(second)["version"] == 2
    assert (
        repo.get_snapshot(first)["payload"]["photos"][0]["sha256"]
        != (repo.get_snapshot(second)["payload"]["photos"][0]["sha256"])
    )


def test_approval_is_user_step_snapshot_bound_and_one_time(tmp_path) -> None:
    repo = CatalogRepository(tmp_path / "catalog.sqlite")
    repo.setup()
    record = repo.issue_approval(
        channel_id="owner",
        item_id="item",
        step="fill_authorization",
        payload={"kind": "fill_authorization", "item_id": "item"},
        snapshot_ids=["snapshot"],
    )

    with pytest.raises(PermissionError):
        repo.consume_approval(
            token=record["token"],
            channel_id="other",
            item_id="item",
            expected_step="fill_authorization",
        )
    consumed = repo.consume_approval(
        token=record["token"],
        channel_id="owner",
        item_id="item",
        expected_step="fill_authorization",
    )
    assert repo.validate_consumed_approval(
        consumed["approval_id"], "item", "fill_authorization", ["snapshot"]
    )
    assert not repo.validate_consumed_approval(
        consumed["approval_id"], "item", "fill_authorization", ["changed"]
    )
    with pytest.raises(PermissionError):
        repo.consume_approval(
            token=record["token"],
            channel_id="owner",
            item_id="item",
            expected_step="fill_authorization",
        )


def test_run_events_round_trip_metadata(tmp_path) -> None:
    repo = CatalogRepository(tmp_path / "catalog.sqlite")
    repo.setup()
    repo.record_run_event(
        "run-1", "item-1", "model", "copy", "ok", {"model": "small", "prompt_tokens": 7}
    )
    assert repo.list_run_events("missing") == []
    rows = repo.list_run_events("run-1")
    assert rows[0]["item_id"] == "item-1"
    assert rows[0]["payload"] == {"model": "small", "prompt_tokens": 7}


def test_copy_diagnostics_are_redacted_and_expire(tmp_path) -> None:
    repo = CatalogRepository(tmp_path / "catalog.sqlite")
    repo.setup()
    repo.record_copy_diagnostic(
        run_id="run-1",
        item_id="item-1",
        portal="olx",
        stage="draft",
        payload={
            "description": "Kontakt: osoba@example.com",
            "token": "token=sekret",
            "model": "iPhone 15 Pro 256 GB",
        },
        retention_days=1,
    )

    row = repo.list_copy_diagnostics("run-1")[0]
    assert "osoba@example.com" not in str(row["payload"])
    assert "sekret" not in str(row["payload"])
    assert row["payload"]["model"] == "iPhone 15 Pro 256 GB"
    assert repo.purge_expired_copy_diagnostics(datetime.now(UTC) + timedelta(days=2)) == 1
    assert repo.list_copy_diagnostics("run-1") == []


def test_copy_rating_is_version_bound_and_redacts_notes(tmp_path) -> None:
    repo = CatalogRepository(tmp_path / "catalog.sqlite")
    repo.setup()
    rating_id = repo.record_copy_rating(
        run_id="run-rating",
        item_id="item-rating",
        portal="olx",
        variant_hash="abc123",
        naturalness=4,
        clarity=5,
        factual_trust=5,
        portal_fit=4,
        usefulness=4,
        notes="kontakt user@example.com token=very-secret-value",
    )

    ratings = repo.list_copy_ratings("run-rating")
    assert ratings[0]["rating_id"] == rating_id
    assert ratings[0]["variant_hash"] == "abc123"
    assert "user@example.com" not in ratings[0]["notes"]
    assert "very-secret-value" not in ratings[0]["notes"]
