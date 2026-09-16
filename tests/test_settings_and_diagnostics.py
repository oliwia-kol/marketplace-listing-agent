import json

import pytest

from marketplace_agent.browser.session import BrowserSessionManager
from marketplace_agent.diagnostics import build_environment_manifest, core_checks
from marketplace_agent.settings import Settings


def test_settings_install_defaults_outside_checkout(tmp_path) -> None:
    settings = Settings(app_dir=tmp_path)
    settings.ensure_directories()

    assert settings.data_dir == tmp_path / "data"
    assert settings.model_config_path == tmp_path / "config" / "models.yaml"
    assert settings.model_config_path.is_file()
    assert "polish_copywriter:\n    model: qwen3.5:9b" in settings.model_config_path.read_text()
    assert settings.source_config_path.is_file()
    assert settings.category_profile_path.is_file()
    assert (settings.golden_dir / "price_math.jsonl").is_file()
    assert (settings.golden_dir / "copy_real_anonymized.jsonl").is_file()
    assert settings.data_dir.stat().st_mode & 0o777 == 0o700
    assert settings.model_config_path.stat().st_mode & 0o777 == 0o600
    manifest = json.loads((tmp_path / "defaults-manifest.json").read_text())
    assert manifest["files"]["config/models.yaml"]["status"] == "current"


def test_settings_preserve_customized_runtime_config(tmp_path) -> None:
    settings = Settings(app_dir=tmp_path)
    settings.ensure_directories()
    settings.model_config_path.write_text("custom: true\n")

    settings.ensure_directories()

    assert settings.model_config_path.read_text() == "custom: true\n"
    manifest = json.loads((tmp_path / "defaults-manifest.json").read_text())
    assert manifest["files"]["config/models.yaml"]["status"] == "customized"

    defaults_check = next(
        result for result in core_checks(settings) if result.name == "installed defaults"
    )
    assert defaults_check.ok is True
    assert defaults_check.detail == "customized: config/models.yaml"


@pytest.mark.asyncio
async def test_research_browser_refuses_unproxied_execution(tmp_path) -> None:
    sessions = BrowserSessionManager(tmp_path / "profile")
    with pytest.raises(RuntimeError, match="research proxy"):
        await sessions.research_context()


def test_core_doctor_has_machine_readable_failures(tmp_path) -> None:
    settings = Settings(app_dir=tmp_path)
    results = core_checks(settings)

    assert results
    assert all(row.ok for row in results)
    assert (tmp_path / "data" / "catalog.sqlite").is_file()


def test_environment_manifest_has_hashes_but_no_private_paths(tmp_path) -> None:
    manifest = build_environment_manifest(Settings(app_dir=tmp_path))
    rendered = str(manifest)

    assert manifest["schema_version"] == 1
    assert len(manifest["goldens_sha256"]) == 10
    assert "polish_copywriter" in manifest["models"]
    assert str(tmp_path) not in rendered
    assert "telegram" not in rendered.casefold()
