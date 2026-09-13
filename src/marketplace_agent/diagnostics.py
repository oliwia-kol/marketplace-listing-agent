from __future__ import annotations

import hashlib
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel

from marketplace_agent.domain.catalog import SCHEMA_VERSION, CatalogRepository
from marketplace_agent.models.ollama_provider import OllamaModelProvider
from marketplace_agent.models.router import ModelRole, ModelRouter, RouterConfig
from marketplace_agent.secrets import read_keychain_token
from marketplace_agent.settings import Settings


@dataclass(frozen=True, slots=True)
class DiagnosticResult:
    name: str
    ok: bool
    detail: str


class DoctorProbe(BaseModel):
    status: str


def build_environment_manifest(settings: Settings) -> dict[str, object]:
    """Return reproducibility metadata without secrets or private content."""
    settings.ensure_directories()

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    assert settings.model_config_path is not None
    assert settings.source_config_path is not None
    assert settings.category_profile_path is not None
    assert settings.golden_dir is not None
    model_config = RouterConfig.model_validate(
        yaml.safe_load(settings.model_config_path.read_text(encoding="utf-8"))
    )
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[2],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=Path(__file__).resolve().parents[2],
                check=True,
                capture_output=True,
                text=True,
                timeout=3,
            ).stdout.strip()
        )
    except (OSError, subprocess.SubprocessError):
        commit, dirty = "unavailable", None
    return {
        "schema_version": 1,
        "git": {"commit": commit, "dirty": dirty},
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "models": {
            role.value: {
                "model": config.model,
                "fallback": config.fallback,
                "context_tokens": config.context_tokens,
                "request_timeout_seconds": config.request_timeout_seconds,
            }
            for role, config in model_config.roles.items()
        },
        "configuration_sha256": {
            "models.yaml": digest(settings.model_config_path),
            "sources.yaml": digest(settings.source_config_path),
            "category_profiles.yaml": digest(settings.category_profile_path),
        },
        "goldens_sha256": {
            path.name: digest(path) for path in sorted(settings.golden_dir.glob("*.jsonl"))
        },
    }


def core_checks(settings: Settings) -> list[DiagnosticResult]:
    results: list[DiagnosticResult] = []
    try:
        settings.ensure_directories()
        directories = [settings.data_dir, settings.reports_dir, settings.golden_dir]
        writable = all(path is not None and os.access(path, os.W_OK) for path in directories)
        results.append(DiagnosticResult("application directories", writable, str(settings.app_dir)))
    except Exception as error:
        return [DiagnosticResult("application directories", False, type(error).__name__)]

    results.append(
        DiagnosticResult(
            "Python",
            sys.version_info >= (3, 12),
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        )
    )
    for name, path in (
        ("models config", settings.model_config_path),
        ("sources config", settings.source_config_path),
        ("category profiles", settings.category_profile_path),
    ):
        try:
            assert path is not None
            parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
            results.append(DiagnosticResult(name, isinstance(parsed, dict), str(path)))
        except Exception as error:
            results.append(DiagnosticResult(name, False, type(error).__name__))

    try:
        repository = CatalogRepository(settings.catalog_db)
        repository.setup()
        with closing(sqlite3.connect(settings.catalog_db)) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            schema = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        ok = integrity is not None and integrity[0] == "ok"
        results.append(DiagnosticResult("catalog database", ok, str(integrity[0])))
        results.append(
            DiagnosticResult(
                "catalog schema",
                schema is not None and schema[0] == SCHEMA_VERSION,
                f"version={schema[0] if schema else 'missing'} expected={SCHEMA_VERSION}",
            )
        )
    except Exception as error:
        results.append(DiagnosticResult("catalog database", False, type(error).__name__))
    return results


def telegram_checks(settings: Settings) -> list[DiagnosticResult]:
    token = settings.telegram_token or read_keychain_token()
    return [
        DiagnosticResult("Telegram token", bool(token), "configured" if token else "missing"),
        DiagnosticResult(
            "Telegram chat ID",
            settings.telegram_allowed_chat_id is not None,
            "configured" if settings.telegram_allowed_chat_id is not None else "missing",
        ),
    ]


def browser_checks(settings: Settings) -> list[DiagnosticResult]:
    chrome_paths = [
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
    ]
    chrome = next((path for path in chrome_paths if path.exists()), None)
    lock_present = (settings.chrome_profile_dir / "SingletonLock").exists()
    return [
        DiagnosticResult("Chrome", chrome is not None, str(chrome or "missing")),
        DiagnosticResult(
            "sales profile lock",
            not lock_present,
            "available" if not lock_present else "SingletonLock present",
        ),
    ]


async def model_checks(settings: Settings, *, probe: bool = True) -> list[DiagnosticResult]:
    if shutil.which("ollama") is None:
        return [DiagnosticResult("Ollama CLI", False, "missing")]
    assert settings.model_config_path is not None
    try:
        router = ModelRouter.from_yaml(OllamaModelProvider(), settings.model_config_path)
        installation = await router.validate_installation()
    except Exception as error:
        return [DiagnosticResult("Ollama server", False, type(error).__name__)]
    results = [DiagnosticResult("Ollama server", True, "reachable")]
    for role, row in installation.items():
        usable = bool(row["installed"] or row["fallback_installed"])
        results.append(
            DiagnosticResult(
                f"model role {role}",
                usable,
                row["model"] if row["installed"] else f"fallback={row['fallback']}",
            )
        )
    if probe and all(row.ok for row in results):
        try:
            response = await router.run(
                ModelRole.VISION_FAST,
                system="Return the requested structured health status.",
                prompt='Return status equal to "ok".',
                output_schema=DoctorProbe,
            )
            results.append(
                DiagnosticResult(
                    "model inference probe",
                    response.output.status.casefold() == "ok",
                    response.model,
                )
            )
        except Exception as error:
            results.append(DiagnosticResult("model inference probe", False, type(error).__name__))
    return results
