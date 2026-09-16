import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from marketplace_agent.domain.catalog import CatalogRepository
from marketplace_agent.domain.models import ItemCase, PortalDraft
from marketplace_agent.mcp_server import MCPFacade


def snapshot_fixture(tmp_path: Path, approved: bool) -> tuple[MCPFacade, ItemCase, str]:
    repo = CatalogRepository(tmp_path / "catalog.sqlite")
    repo.setup()
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(b"photo")
    item = ItemCase(photo_paths=[photo], selected_portals=["olx"])
    draft = PortalDraft(
        portal="olx", title="Tytuł", description="Opis", category="Inne", price_pln=20
    )
    snapshot_id = repo.create_listing_snapshot(item, draft)
    item.snapshot_ids = {"olx": snapshot_id}
    repo.save_item(item)
    if approved:
        record = repo.issue_approval(
            channel_id="owner",
            item_id=item.item_id,
            step="fill_authorization",
            payload={"snapshot_ids": [snapshot_id]},
            snapshot_ids=[snapshot_id],
        )
        repo.consume_approval(
            token=record["token"],
            channel_id="owner",
            item_id=item.item_id,
            expected_step="fill_authorization",
        )
    return MCPFacade(repo), item, snapshot_id


def test_mcp_returns_narrow_item_status(tmp_path: Path) -> None:
    facade, item, _ = snapshot_fixture(tmp_path, approved=True)
    result = facade.get_item_status(item.item_id)
    assert result["item_id"] == item.item_id
    assert "facts" not in result


def test_mcp_refuses_unapproved_snapshot(tmp_path: Path) -> None:
    facade, _, snapshot_id = snapshot_fixture(tmp_path, approved=False)
    with pytest.raises(PermissionError):
        facade.get_approved_snapshot(snapshot_id)


def test_mcp_does_not_accept_new_content_or_price(tmp_path: Path) -> None:
    facade, _, _ = snapshot_fixture(tmp_path, approved=True)
    assert "price" not in facade.execute_approved_listing.__annotations__
    assert "description" not in facade.execute_approved_listing.__annotations__


@pytest.mark.asyncio
async def test_mcp_server_completes_a_real_stdio_handshake(tmp_path: Path) -> None:
    environment = os.environ.copy()
    environment["MARKETPLACE_AGENT_APP_DIR"] = str(tmp_path / "app")
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "marketplace_agent.mcp_server"],
        env=environment,
        cwd=Path(__file__).parents[1],
    )

    async with (
        stdio_client(parameters) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        tools = await session.list_tools()

    names = {tool.name for tool in tools.tools}
    assert {
        "get_item_status",
        "get_approved_snapshot",
        "get_pricing_evidence_summary",
        "execute_approved_listing",
        "get_execution_status",
        "resume_execution",
        "cancel_execution",
    } == names
