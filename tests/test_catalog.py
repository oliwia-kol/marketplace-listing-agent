from marketplace_agent.domain.catalog import CatalogRepository
from marketplace_agent.domain.models import ItemCase


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
