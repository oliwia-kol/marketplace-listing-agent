from __future__ import annotations

import os
import sys
from importlib.resources import files
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def default_app_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Marketplace Listing Agent"
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    return (
        Path(xdg_data_home) / "marketplace-listing-agent"
        if xdg_data_home
        else (Path.home() / ".local" / "share" / "marketplace-listing-agent")
    )


class Settings(BaseSettings):
    """Runtime configuration. Secrets can come from env or macOS Keychain."""

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="MARKETPLACE_AGENT_", extra="ignore"
    )

    app_dir: Path = Field(default_factory=default_app_dir)
    data_dir: Path | None = None
    reports_dir: Path | None = None
    model_config_path: Path | None = None
    source_config_path: Path | None = None
    category_profile_path: Path | None = None
    golden_dir: Path | None = None
    telegram_token: str | None = None
    telegram_allowed_chat_id: int | None = None
    headless: bool = False
    allow_live_submit: bool = False
    log_level: str = "INFO"

    @model_validator(mode="after")
    def resolve_paths(self) -> Settings:
        self.data_dir = self.data_dir or self.app_dir / "data"
        self.reports_dir = self.reports_dir or self.app_dir / "reports"
        config_dir = self.app_dir / "config"
        self.model_config_path = self.model_config_path or config_dir / "models.yaml"
        self.source_config_path = self.source_config_path or config_dir / "sources.yaml"
        self.category_profile_path = (
            self.category_profile_path or config_dir / "category_profiles.yaml"
        )
        self.golden_dir = self.golden_dir or self.app_dir / "goldens"
        return self

    @property
    def checkpoint_db(self) -> Path:
        assert self.data_dir is not None
        return self.data_dir / "checkpoints.sqlite"

    @property
    def catalog_db(self) -> Path:
        assert self.data_dir is not None
        return self.data_dir / "catalog.sqlite"

    @property
    def chrome_profile_dir(self) -> Path:
        assert self.data_dir is not None
        return self.data_dir / "chrome-profile"

    def ensure_directories(self) -> None:
        assert self.data_dir is not None
        assert self.reports_dir is not None
        assert self.golden_dir is not None
        self.app_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        for directory in (self.app_dir, self.data_dir, self.reports_dir, self.chrome_profile_dir):
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            directory.chmod(0o700)
        self._install_defaults()

    def _install_defaults(self) -> None:
        config_targets = {
            "models.yaml": self.model_config_path,
            "sources.yaml": self.source_config_path,
            "category_profiles.yaml": self.category_profile_path,
        }
        for name, target in config_targets.items():
            assert target is not None
            self._copy_default("config", name, target)
        assert self.golden_dir is not None
        for name in (
            "comparables.jsonl",
            "copy.jsonl",
            "copy_audit.jsonl",
            "facts.jsonl",
            "forms.jsonl",
            "price_math.jsonl",
        ):
            self._copy_default("goldens", name, self.golden_dir / name)

    def _copy_default(self, kind: str, name: str, target: Path) -> None:
        if target.exists():
            return
        source_checkout = PROJECT_ROOT / kind / name
        content = (
            source_checkout.read_bytes()
            if source_checkout.exists()
            else files("marketplace_agent").joinpath("defaults", kind, name).read_bytes()
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        target.chmod(0o600)
