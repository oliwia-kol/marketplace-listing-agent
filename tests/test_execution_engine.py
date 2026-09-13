import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from marketplace_agent.domain.catalog import CatalogRepository
from marketplace_agent.domain.models import ItemCase, PortalDraft
from marketplace_agent.execution.engine import (
    BrowserExecutionAdapter,
    ExecutionEngine,
    PreparationResult,
)


class AdapterStub:
    def __init__(self, result: PreparationResult) -> None:
        self.result = result
        self.calls = 0

    async def prepare(self, snapshot):
        self.calls += 1
        return self.result

    async def publish(self, snapshot, previous_result):
        self.calls += 1
        return self.result

    async def reconcile(self, snapshot):
        self.calls += 1
        return self.result


def approved_job(tmp_path: Path) -> tuple[CatalogRepository, dict]:
    repo = CatalogRepository(tmp_path / "catalog.sqlite")
    repo.setup()
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(b"photo")
    item = ItemCase(photo_paths=[photo])
    draft = PortalDraft(
        portal="olx", title="Przedmiot", description="Opis", category="Inne", price_pln=100
    )
    snapshot_id = repo.create_listing_snapshot(item, draft)
    approval = repo.issue_approval(
        channel_id="owner",
        item_id=item.item_id,
        step="fill_authorization",
        payload={"snapshot_ids": [snapshot_id]},
        snapshot_ids=[snapshot_id],
    )
    consumed = repo.consume_approval(
        token=approval["token"],
        channel_id="owner",
        item_id=item.item_id,
        expected_step="fill_authorization",
    )
    return repo, repo.enqueue_execution(
        approval_id=consumed["approval_id"], snapshot_id=snapshot_id, portal="olx"
    )


@pytest.mark.asyncio
async def test_engine_is_idempotent_and_moves_job_to_ready(tmp_path: Path) -> None:
    repo, job = approved_job(tmp_path)
    duplicate = repo.enqueue_execution(
        approval_id=job["approval_id"], snapshot_id=job["snapshot_id"], portal="olx"
    )
    assert duplicate["job_id"] == job["job_id"]
    adapter = AdapterStub(PreparationResult("ready", {"readback": "matched"}))
    result = await ExecutionEngine(repo, adapter, "worker-1").run_once()
    assert result["status"] == "ready"
    assert result["attempt"] == 1
    assert adapter.calls == 1
    assert await ExecutionEngine(repo, adapter, "worker-2").run_once() is None


@pytest.mark.asyncio
async def test_engine_persists_single_intervention_and_requires_explicit_resume(
    tmp_path: Path,
) -> None:
    repo, job = approved_job(tmp_path)
    adapter = AdapterStub(
        PreparationResult("waiting_user", {"url": "fixture"}, "captcha", "Rozwiąż CAPTCHA")
    )
    result = await ExecutionEngine(repo, adapter, "worker-1").run_once()
    assert result["status"] == "waiting_user"
    intervention_id = result["result"]["intervention_id"]
    intervention = repo.get_intervention(intervention_id)
    assert intervention["kind"] == "captcha"
    repo.resume_intervention(job["job_id"], intervention_id)
    assert repo.get_execution_job(job["job_id"])["status"] == "queued"


def test_emergency_stop_cancels_queued_work(tmp_path: Path) -> None:
    repo, job = approved_job(tmp_path)
    assert repo.emergency_stop() == 1
    assert repo.get_execution_job(job["job_id"])["status"] == "cancelled"


def test_stale_prepare_is_requeued_but_stale_submit_is_never_retried(tmp_path: Path) -> None:
    repo, job = approved_job(tmp_path)
    with closing(sqlite3.connect(repo.database_path)) as connection:
        connection.execute(
            "UPDATE execution_jobs SET status='preparing', locked_by='dead', locked_at=?",
            ("2000-01-01T00:00:00+00:00",),
        )
        connection.commit()
    assert repo.recover_stale_executions() == {
        "requeued_prepare": 1,
        "unknown_submit": 0,
    }
    assert repo.get_execution_job(job["job_id"])["status"] == "queued"

    with closing(sqlite3.connect(repo.database_path)) as connection:
        connection.execute(
            "UPDATE execution_jobs SET status='submitting', locked_by='dead', locked_at=?",
            ("2000-01-01T00:00:00+00:00",),
        )
        connection.commit()
    assert repo.recover_stale_executions() == {
        "requeued_prepare": 0,
        "unknown_submit": 1,
    }
    recovered = repo.get_execution_job(job["job_id"])
    assert recovered["status"] == "unknown"
    assert recovered["result"]["reason"] == "stale_submit_requires_reconciliation"


def test_adapter_rechecks_photo_hash_at_each_boundary(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    photo_dir = data_dir / "items" / "item-1" / "photos"
    photo_dir.mkdir(parents=True)
    photo = photo_dir / "01.jpg"
    photo.write_bytes(b"approved")
    import hashlib

    snapshot = {
        "item_id": "item-1",
        "payload": {
            "photos": [
                {
                    "index": 0,
                    "file_name": "01.jpg",
                    "sha256": hashlib.sha256(b"approved").hexdigest(),
                }
            ]
        },
    }
    adapter = BrowserExecutionAdapter(None, None, data_dir)  # type: ignore[arg-type]
    assert adapter._verified_photo_paths(snapshot) == [photo]
    photo.write_bytes(b"changed after approval")
    assert adapter._verified_photo_paths(snapshot) is None


@pytest.mark.asyncio
async def test_publication_requires_separate_snapshot_bound_approval(tmp_path: Path) -> None:
    repo, job = approved_job(tmp_path)
    repo.set_execution_status(job["job_id"], "ready", {"filled_fields": {"title": "Przedmiot"}})
    snapshot = repo.get_snapshot(job["snapshot_id"])
    approval = repo.issue_approval(
        channel_id="owner",
        item_id=snapshot["item_id"],
        step="publish_authorization",
        payload={"job_id": job["job_id"]},
        snapshot_ids=[job["snapshot_id"]],
    )
    consumed = repo.consume_approval(
        token=approval["token"],
        channel_id="owner",
        item_id=snapshot["item_id"],
        expected_step="publish_authorization",
    )
    repo.attach_publish_approval(job["job_id"], consumed["approval_id"])
    adapter = AdapterStub(PreparationResult("published", {"url": "https://example.test/ad/1"}))
    result = await ExecutionEngine(repo, adapter, "worker-1").run_once()
    assert result["status"] == "published"
    assert result["attempt"] == 1
