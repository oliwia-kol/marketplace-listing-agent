from __future__ import annotations

import asyncio
import getpass
import shutil
from pathlib import Path

import typer

from marketplace_agent.channels.telegram import TelegramChannel
from marketplace_agent.evaluation.runner import EvaluationRunner
from marketplace_agent.models.ollama_provider import OllamaModelProvider
from marketplace_agent.models.router import ModelRouter
from marketplace_agent.runtime import ApplicationRuntime
from marketplace_agent.secrets import read_keychain_token, save_keychain_token
from marketplace_agent.settings import Settings

app = typer.Typer(no_args_is_help=True, help="Lokalny asystent przygotowywania ofert.")


def _settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings


@app.command("configure-token")
def configure_token() -> None:
    """Zapisz token Telegrama w pęku kluczy macOS."""
    token = getpass.getpass("Token bota Telegram (nie zostanie wyświetlony): ")
    if not token.strip():
        raise typer.BadParameter("Token nie może być pusty")
    save_keychain_token(token.strip())
    typer.echo("Token zapisany w macOS Keychain.")


@app.command()
def doctor() -> None:
    """Sprawdź środowisko, konfigurację i dostępność modeli."""

    async def inspect() -> None:
        settings = _settings()
        token = settings.telegram_token or read_keychain_token()
        chrome_paths = [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        ]
        typer.echo(f"Python/config: OK ({settings.model_config_path})")
        typer.echo(f"Chrome: {'OK' if any(path.exists() for path in chrome_paths) else 'BRAK'}")
        typer.echo(f"Ollama CLI: {'OK' if shutil.which('ollama') else 'BRAK'}")
        typer.echo(f"Telegram token: {'OK' if token else 'BRAK'}")
        typer.echo(
            f"Telegram chat ID: {'OK' if settings.telegram_allowed_chat_id is not None else 'BRAK'}"
        )
        try:
            router = ModelRouter.from_yaml(OllamaModelProvider(), settings.model_config_path)
            status = await router.validate_installation()
        except Exception as error:
            typer.echo(f"Ollama server: BŁĄD ({error})")
            return
        typer.echo("Modele:")
        for role, row in status.items():
            marker = "OK" if row["installed"] else "BRAK"
            fallback = (
                f"; fallback={row['fallback']} ({'OK' if row['fallback_installed'] else 'BRAK'})"
                if row["fallback"]
                else ""
            )
            typer.echo(f"  {role}: {row['model']} ({marker}){fallback}")

    asyncio.run(inspect())


@app.command()
def run() -> None:
    """Uruchom kanał Telegram i trwały workflow."""

    async def serve() -> None:
        settings = _settings()
        token = settings.telegram_token or read_keychain_token()
        if not token:
            raise RuntimeError("Brak tokenu. Uruchom: marketplace-listing-agent configure-token")
        if settings.telegram_allowed_chat_id is None:
            raise RuntimeError("Ustaw MARKETPLACE_AGENT_TELEGRAM_ALLOWED_CHAT_ID w .env")
        async with ApplicationRuntime(settings) as runtime:
            assert runtime.catalog is not None
            channel = TelegramChannel(
                token,
                settings.telegram_allowed_chat_id,
                runtime.graph,
                runtime.catalog,
                settings.data_dir,
            )
            await channel.run()

    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        typer.echo("Zatrzymano.")


@app.command("show-config")
def show_config() -> None:
    """Pokaż bezpieczną część konfiguracji."""
    settings = _settings()
    typer.echo(f"Dane: {settings.data_dir}")
    typer.echo(f"Modele: {settings.model_config_path}")
    typer.echo(f"Źródła: {settings.source_config_path}")
    typer.echo(f"Tryb headless: {settings.headless}")


@app.command("eval")
def evaluate(
    suite: str = typer.Option(
        "price_math", help="price_math, facts, comparables, copy, copy_audit albo forms"
    ),
    model: str | None = typer.Option(None, help="Jednorazowa podmiana modelu dla roli"),
) -> None:
    """Uruchom wybrany zestaw golden i zapisz raport JSON."""

    async def execute() -> None:
        settings = _settings()
        router = ModelRouter.from_yaml(OllamaModelProvider(), settings.model_config_path)
        runner = EvaluationRunner(
            router,
            settings.model_config_path.parent.parent / "goldens",
            settings.reports_dir,
        )
        report = await runner.run(suite, model)
        typer.echo(f"Raport: {report}")

    asyncio.run(execute())
