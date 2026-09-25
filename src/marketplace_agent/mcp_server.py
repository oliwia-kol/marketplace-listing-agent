from __future__ import annotations

from typing import Any
from uuid import uuid4

from mcp.server.mcpserver import MCPServer

from marketplace_agent.domain.catalog import CatalogRepository
from marketplace_agent.settings import Settings


class MCPFacade:
    """Narrow application boundary shared by MCP tools and unit tests."""

    def __init__(self, catalog: CatalogRepository) -> None:
        self.catalog = catalog

    def _audit(self, operation: str, status: str, payload: dict[str, Any]) -> None:
        self.catalog.record_run_event(uuid4().hex, None, "mcp", operation, status, payload)

    def get_item_status(self, item_id: str) -> dict[str, Any]:
        item = self.catalog.get_item(item_id)
        if item is None:
            self._audit("get_item_status", "error", {"error_type": "NotFound"})
            raise ValueError("item not found")
        jobs = self.catalog.list_execution_jobs(item_id)
        result = {
            "item_id": item.item_id,
            "status": item.status.value,
            "portals": item.selected_portals,
            "snapshot_ids": item.snapshot_ids,
            "jobs": [
                {"job_id": job["job_id"], "portal": job["portal"], "status": job["status"]}
                for job in jobs
            ],
        }
        self._audit("get_item_status", "ok", {"item_id": item_id})
        return result

    def get_approved_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        snapshot = self.catalog.get_snapshot(snapshot_id)
        if snapshot is None or not self.catalog.is_snapshot_approved(snapshot_id):
            self._audit("get_approved_snapshot", "error", {"error_type": "NotApproved"})
            raise PermissionError("snapshot is missing or not approved")
        result = {
            "snapshot_id": snapshot["snapshot_id"],
            "item_id": snapshot["item_id"],
            "version": snapshot["version"],
            "portal": snapshot["portal"],
            "content_hash": snapshot["content_hash"],
            "draft": snapshot["payload"]["draft"],
            "photos": snapshot["payload"]["photos"],
        }
        self._audit("get_approved_snapshot", "ok", {"snapshot_id": snapshot_id})
        return result

    def get_pricing_evidence_summary(self, item_id: str) -> dict[str, Any]:
        item = self.catalog.get_item(item_id)
        if item is None or item.price_summary is None:
            self._audit("get_pricing_evidence_summary", "error", {"error_type": "NotFound"})
            raise ValueError("pricing summary not found")
        result = item.price_summary.model_dump(mode="json")
        # A host path is unnecessary to an MCP client and reveals local layout.
        result.pop("evidence_manifest_path", None)
        self._audit("get_pricing_evidence_summary", "ok", {"item_id": item_id})
        return result

    def execute_approved_listing(self, job_id: str) -> dict[str, Any]:
        job = self.catalog.get_execution_job(job_id)
        if job is None:
            raise ValueError("job not found")
        if not self.catalog.is_snapshot_approved(job["snapshot_id"]):
            self._audit("execute_approved_listing", "error", {"error_type": "NotApproved"})
            raise PermissionError("job snapshot is not approved")
        if job["status"] == "ready" and not job["publish_approval_id"]:
            return {"job_id": job_id, "status": "ready", "requires": "publish_authorization"}
        if job["status"] == "authorized_to_publish":
            snapshot = self.catalog.get_snapshot(job["snapshot_id"])
            assert snapshot is not None
            if not self.catalog.validate_consumed_approval(
                job["publish_approval_id"],
                snapshot["item_id"],
                "publish_authorization",
                [job["snapshot_id"]],
            ):
                raise PermissionError("publish approval no longer matches the snapshot")
        elif job["status"] not in {"queued", "preparing", "waiting_user"}:
            raise PermissionError(f"job cannot execute from status {job['status']}")
        self._audit("execute_approved_listing", "ok", {"job_id": job_id})
        return {"job_id": job_id, "status": job["status"], "worker_required": True}

    def get_execution_status(self, job_id: str) -> dict[str, Any]:
        job = self.catalog.get_execution_job(job_id)
        if job is None:
            raise ValueError("job not found")
        self._audit("get_execution_status", "ok", {"job_id": job_id})
        return {key: value for key, value in job.items() if key not in {"idempotency_key"}}

    def resume_execution(self, job_id: str, intervention_id: str) -> dict[str, str]:
        self.catalog.resume_intervention(job_id, intervention_id)
        self._audit("resume_execution", "ok", {"job_id": job_id})
        return {"job_id": job_id, "status": "queued"}

    def cancel_execution(self, job_id: str) -> dict[str, str]:
        self.catalog.cancel_execution(job_id)
        self._audit("cancel_execution", "ok", {"job_id": job_id})
        return {"job_id": job_id, "status": "cancelled"}


def build_mcp_server(settings: Settings) -> MCPServer:
    settings.ensure_directories()
    catalog = CatalogRepository(settings.catalog_db)
    catalog.setup()
    facade = MCPFacade(catalog)
    server = MCPServer(
        "marketplace-listing-agent",
        instructions=(
            "Local read and execution-control tools. Never pass passwords, OTPs, cookies, "
            "new listing content or prices."
        ),
    )
    server.tool()(facade.get_item_status)
    server.tool()(facade.get_approved_snapshot)
    server.tool()(facade.get_pricing_evidence_summary)
    server.tool()(facade.execute_approved_listing)
    server.tool()(facade.get_execution_status)
    server.tool()(facade.resume_execution)
    server.tool()(facade.cancel_execution)
    return server


def main() -> None:
    build_mcp_server(Settings()).run(transport="stdio")


if __name__ == "__main__":
    main()
