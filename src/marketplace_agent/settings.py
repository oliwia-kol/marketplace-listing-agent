from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration. Secrets can come from env or macOS Keychain."""

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="MARKETPLACE_AGENT_", extra="ignore"
    )

    data_dir: Path = Field(default=PROJECT_ROOT / "data")
    reports_dir: Path = Field(default=PROJECT_ROOT / "reports")
    model_config_path: Path = Field(default=PROJECT_ROOT / "config" / "models.yaml")
    source_config_path: Path = Field(default=PROJECT_ROOT / "config" / "sources.yaml")
    category_profile_path: Path = Field(default=PROJECT_ROOT / "config" / "category_profiles.yaml")
    telegram_token: str | None = None
    telegram_allowed_chat_id: int | None = None
    headless: bool = False
    log_level: str = "INFO"

    @property
    def checkpoint_db(self) -> Path:
        return self.data_dir / "checkpoints.sqlite"

    @property
    def catalog_db(self) -> Path:
        return self.data_dir / "catalog.sqlite"

    @property
    def chrome_profile_dir(self) -> Path:
        return self.data_dir / "chrome-profile"

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.chrome_profile_dir.mkdir(parents=True, exist_ok=True)
