from __future__ import annotations

import asyncio
import getpass
import json
import os
import socket
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from marketplace_agent.channels.telegram import TelegramChannel
from marketplace_agent.diagnostics import (
    browser_checks,
    build_environment_manifest,
    core_checks,
    model_checks,
    research_checks,
    telegram_checks,
)
from marketplace_agent.evaluation.runner import EvaluationRunner
from marketplace_agent.execution.engine import BrowserExecutionAdapter, ExecutionEngine
from marketplace_agent.models.ollama_provider import OllamaModelProvider
from marketplace_agent.models.router import ModelRouter
from marketplace_agent.monitoring.report import write_copy_report, write_run_report
from marketplace_agent.runtime import ApplicationRuntime
from marketplace_agent.secrets import read_keychain_token, save_keychain_token
from marketplace_agent.settings import Settings

app = typer.Typer(no_args_is_help=True, help="Lokalny asystent przygotowywania ofert.")


class DoctorScope(StrEnum):
    CORE = "core"
    TELEGRAM = "telegram"
    MODELS = "models"
    BROWSER = "browser"
    RESEARCH = "research"
    ALL = "all"


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
def doctor(
    scope: Annotated[DoctorScope, typer.Option("--scope")] = DoctorScope.CORE,
    probe: Annotated[bool, typer.Option("--probe/--no-probe")] = True,
) -> None:
    """Sprawdź środowisko, konfigurację i dostępność modeli."""

    async def inspect() -> bool:
        settings = Settings()
        selected = (
            {scope}
            if scope != DoctorScope.ALL
            else {
                DoctorScope.CORE,
                DoctorScope.TELEGRAM,
                DoctorScope.MODELS,
                DoctorScope.BROWSER,
                DoctorScope.RESEARCH,
            }
        )
        results = []
        if DoctorScope.CORE in selected:
            results.extend(core_checks(settings))
        if DoctorScope.TELEGRAM in selected:
            results.extend(telegram_checks(settings))
        if DoctorScope.BROWSER in selected:
            results.extend(browser_checks(settings))
        if DoctorScope.RESEARCH in selected:
            results.extend(research_checks(settings))
        if DoctorScope.MODELS in selected:
            settings.ensure_directories()
            results.extend(await model_checks(settings, probe=probe))
        for row in results:
            typer.echo(f"[{'OK' if row.ok else 'FAIL'}] {row.name}: {row.detail}")
        return all(row.ok for row in results)

    if not asyncio.run(inspect()):
        raise typer.Exit(code=1)


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
        assert settings.data_dir is not None
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
    assert settings.data_dir is not None
    typer.echo(f"Dane: {settings.data_dir}")
    typer.echo(f"Modele: {settings.model_config_path}")
    typer.echo(f"Źródła: {settings.source_config_path}")
    typer.echo(f"Tryb headless: {settings.headless}")


@app.command("manifest")
def manifest(
    destination: Annotated[
        Path, typer.Option(help="Plik JSON na bezpieczne metadane odtwarzalności")
    ] = Path("environment-manifest.json"),
) -> None:
    """Zapisz wersje i hashe konfiguracji bez sekretów i treści prywatnych."""
    payload = build_environment_manifest(_settings())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    destination.chmod(0o600)
    typer.echo(f"Manifest: {destination}")


@app.command("eval")
def evaluate(
    suite: str = typer.Option(
        "price_math",
        help=(
            "price_math, facts, comparables, copy, copy_quality, copy_generalization, "
            "copy_real_anonymized, copy_audit, copy_audit_mutations albo forms"
        ),
    ),
    model: str | None = typer.Option(None, help="Jednorazowa podmiana modelu dla roli"),
    repeats: int = typer.Option(1, min=1, max=10, help="Liczba powtórzeń każdego przypadku"),
    temperature: float | None = typer.Option(None, min=0, max=2),
    top_p: float | None = typer.Option(None, min=0.01, max=1),
    top_k: int | None = typer.Option(None, min=1),
    seed: int | None = typer.Option(None),
    split: str | None = typer.Option(
        None, help="Opcjonalny split zestawu, np. development, selection lub frozen"
    ),
    limit: int | None = typer.Option(None, min=1, help="Maksymalna liczba przypadków na próbę"),
    case_ids: str | None = typer.Option(
        None,
        help=(
            "Lista identyfikatorów rozdzielonych przecinkami; przydatna do "
            "zbalansowanego screeningu"
        ),
    ),
) -> None:
    """Uruchom wybrany zestaw golden i zapisz raport JSON."""

    async def execute() -> None:
        settings = _settings()
        assert settings.model_config_path is not None
        assert settings.data_dir is not None
        assert settings.golden_dir is not None
        assert settings.reports_dir is not None
        router = ModelRouter.from_yaml(OllamaModelProvider(), settings.model_config_path)
        runner = EvaluationRunner(
            router,
            settings.golden_dir,
            settings.reports_dir,
        )
        report = await runner.run(
            suite,
            model,
            repeats=repeats,
            generation_overrides={
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "seed": seed,
            },
            split=split,
            limit=limit,
            case_ids={value.strip() for value in case_ids.split(",") if value.strip()}
            if case_ids
            else None,
        )
        typer.echo(f"Raport: {report}")

    asyncio.run(execute())


@app.command("report")
def report(
    run_id: str = typer.Option(..., help="Identyfikator przebiegu zapisany w SQLite"),
) -> None:
    """Wygeneruj lokalny, pozbawiony treści wrażliwych raport HTML."""
    settings = _settings()
    assert settings.reports_dir is not None
    from marketplace_agent.domain.catalog import CatalogRepository

    catalog = CatalogRepository(settings.catalog_db)
    catalog.setup()
    events = catalog.list_run_events(run_id)
    if not events:
        raise typer.BadParameter("Nie znaleziono zdarzeń dla tego przebiegu")
    typer.echo(f"Raport: {write_run_report(events, settings.reports_dir, run_id)}")


@app.command("copy-report")
def copy_report(
    run_id: str = typer.Option(..., help="Identyfikator przebiegu zapisany w SQLite"),
) -> None:
    """Wygeneruj lokalny raport briefu, draftów, audytu i poprawek opisu."""
    settings = _settings()
    assert settings.reports_dir is not None
    from marketplace_agent.domain.catalog import CatalogRepository

    catalog = CatalogRepository(settings.catalog_db)
    catalog.setup()
    diagnostics = catalog.list_copy_diagnostics(run_id)
    if not diagnostics:
        raise typer.BadParameter("Nie znaleziono diagnostyki opisu dla tego przebiegu")
    ratings = catalog.list_copy_ratings(run_id)
    typer.echo(f"Raport: {write_copy_report(diagnostics, settings.reports_dir, run_id, ratings)}")


@app.command("copy-rate")
def copy_rate(
    run_id: str = typer.Option(...),
    item_id: str = typer.Option(...),
    portal: str = typer.Option(...),
    variant_hash: str = typer.Option(..., help="Hash wariantu z raportu lub eksperymentu"),
    naturalness: int = typer.Option(..., min=1, max=5),
    clarity: int = typer.Option(..., min=1, max=5),
    factual_trust: int = typer.Option(..., min=1, max=5),
    portal_fit: int = typer.Option(..., min=1, max=5),
    usefulness: int = typer.Option(..., min=1, max=5),
    notes: str | None = typer.Option(None),
) -> None:
    """Zapisz lokalną ocenę człowieka dla konkretnej wersji opisu."""
    from marketplace_agent.domain.catalog import CatalogRepository

    settings = _settings()
    catalog = CatalogRepository(settings.catalog_db)
    catalog.setup()
    rating_id = catalog.record_copy_rating(
        run_id=run_id,
        item_id=item_id,
        portal=portal,
        variant_hash=variant_hash,
        naturalness=naturalness,
        clarity=clarity,
        factual_trust=factual_trust,
        portal_fit=portal_fit,
        usefulness=usefulness,
        notes=notes,
    )
    typer.echo(f"Ocena: {rating_id}")


@app.command("worker")
def worker(
    once: bool = typer.Option(False, "--once", help="Obsłuż najwyżej jedno zadanie"),
) -> None:
    """Uruchom oddzielny proces deterministycznego wykonawcy formularzy."""

    async def execute() -> None:
        settings = _settings()
        assert settings.model_config_path is not None
        from marketplace_agent.browser.session import BrowserSessionManager
        from marketplace_agent.domain.catalog import CatalogRepository

        catalog = CatalogRepository(settings.catalog_db)
        catalog.setup()
        router = ModelRouter.from_yaml(
            OllamaModelProvider(), settings.model_config_path, event_sink=catalog.record_run_event
        )
        sessions = BrowserSessionManager(settings.chrome_profile_dir, headless=False)
        engine = ExecutionEngine(
            catalog,
            BrowserExecutionAdapter(
                sessions,
                router,
                settings.data_dir,
                allow_live_submit=settings.allow_live_submit,
            ),
            f"{socket.gethostname()}:{os.getpid()}",
        )
        try:
            while True:
                recovered = catalog.recover_stale_executions()
                if any(recovered.values()):
                    typer.echo(f"Odzyskane dzierżawy: {recovered}")
                result = await engine.run_once()
                if result:
                    typer.echo(f"{result['job_id']}: {result['status']}")
                if once:
                    return
                await asyncio.sleep(2)
        finally:
            await sessions.close()

    asyncio.run(execute())


@app.command("resume-job")
def resume_job(job_id: str, intervention_id: str) -> None:
    """Wznów jedno zadanie po ręcznym usunięciu przeszkody."""
    from marketplace_agent.domain.catalog import CatalogRepository

    settings = _settings()
    catalog = CatalogRepository(settings.catalog_db)
    catalog.setup()
    catalog.resume_intervention(job_id, intervention_id)
    typer.echo("Zadanie wróciło do kolejki; worker ponownie sprawdzi stronę.")


@app.command("cancel-job")
def cancel_job(job_id: str) -> None:
    """Anuluj jedno zadanie wykonawcze."""
    from marketplace_agent.domain.catalog import CatalogRepository

    settings = _settings()
    catalog = CatalogRepository(settings.catalog_db)
    catalog.setup()
    catalog.cancel_execution(job_id)
    typer.echo("Zadanie anulowane.")


@app.command("emergency-stop")
def emergency_stop() -> None:
    """Anuluj wszystkie oczekujące i aktywne zadania wykonawcze."""
    from marketplace_agent.domain.catalog import CatalogRepository

    settings = _settings()
    catalog = CatalogRepository(settings.catalog_db)
    catalog.setup()
    typer.echo(f"Anulowane zadania: {catalog.emergency_stop()}")


@app.command("reconcile-job")
def reconcile_job(job_id: str) -> None:
    """Sprawdź niepewny wynik publikacji bez ponownego klikania submit."""

    async def execute() -> None:
        settings = _settings()
        assert settings.model_config_path is not None
        assert settings.data_dir is not None
        from marketplace_agent.browser.session import BrowserSessionManager
        from marketplace_agent.domain.catalog import CatalogRepository

        catalog = CatalogRepository(settings.catalog_db)
        catalog.setup()
        router = ModelRouter.from_yaml(OllamaModelProvider(), settings.model_config_path)
        sessions = BrowserSessionManager(settings.chrome_profile_dir, headless=False)
        engine = ExecutionEngine(
            catalog,
            BrowserExecutionAdapter(sessions, router, settings.data_dir),
            "reconciler",
        )
        try:
            result = await engine.reconcile(job_id)
            typer.echo(f"{job_id}: {result['status']}")
        finally:
            await sessions.close()

    asyncio.run(execute())


@app.command("backup")
def backup(
    destination: Annotated[Path, typer.Option(help="Katalog nadrzędny kopii")],
) -> None:
    """Utwórz spójną kopię baz SQLite za pomocą SQLite Backup API."""
    from marketplace_agent.operations.backup import create_backup

    settings = _settings()
    assert settings.data_dir is not None
    config_paths = tuple(
        path
        for path in (
            settings.model_config_path,
            settings.source_config_path,
            settings.category_profile_path,
        )
        if path is not None
    )
    typer.echo(
        "Kopia: "
        + str(
            create_backup(
                settings.catalog_db,
                settings.checkpoint_db,
                destination,
                data_dir=settings.data_dir,
                config_paths=config_paths,
            )
        )
    )


@app.command("restore-backup")
def restore(source: Path, destination_app_dir: Path) -> None:
    """Odtwórz kopię do nowego, pustego katalogu aplikacji."""
    from marketplace_agent.operations.backup import restore_backup

    restored = restore_backup(source, destination_app_dir)
    typer.echo("Odtworzono: " + ", ".join(str(path) for path in restored))
