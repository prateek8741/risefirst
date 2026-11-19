"""Command line: `risefirst migrate | ingest | schedule | stats`."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import typer

from risefirst.composition import build_ingestion, build_repository
from risefirst.config import get_settings
from risefirst.infrastructure.http import PoliteHttpClient

app = typer.Typer(help="RiseFirst job pipeline", no_args_is_help=True)
IST = ZoneInfo("Asia/Kolkata")
log = logging.getLogger("risefirst")


def _setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google_genai").setLevel(logging.WARNING)


@app.command()
def migrate() -> None:
    """Apply database migrations (alembic upgrade head)."""
    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parents[3]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    command.upgrade(config, "head")
    typer.echo("database is up to date")


@app.command()
def ingest(
    source: str | None = typer.Option(None, help="Only this board, e.g. 'stripe' or 'lever:paytm'"),
    no_ai: bool = typer.Option(False, "--no-ai", help="Rules only, even if GEMINI_API_KEY is set"),
) -> None:
    """Fetch all sources, classify, and update the database once."""
    _setup_logging()
    settings = get_settings()
    log.info("AI enrichment: %s", f"on ({settings.gemini_model})" if settings.ai_enabled and not no_ai else "off")
    http = PoliteHttpClient(settings.http_timeout_seconds)
    try:
        report = build_ingestion(settings, http, source, use_ai=not no_ai).run()
    finally:
        http.close()
    summary = {k: v for k, v in vars(report).items() if k not in {"sources_ok"}}
    summary["sources_ok"] = len(report.sources_ok)
    typer.echo(json.dumps(summary, indent=2, default=str))


def _next_run(now: datetime, hour: int) -> datetime:
    local = now.astimezone(IST)
    target = local.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= local:
        target += timedelta(days=1)
    return target.astimezone(UTC)


@app.command()
def schedule(run_now: bool = typer.Option(True, help="Run once immediately on start")) -> None:
    """Run ingestion every day at REFRESH_HOUR_IST (default 06:00 IST). Used by the worker container."""
    _setup_logging()
    settings = get_settings()
    if run_now:
        _safe_ingest()
    while True:
        next_run = _next_run(datetime.now(UTC), settings.refresh_hour_ist)
        log.info("next refresh at %s IST", next_run.astimezone(IST).strftime("%Y-%m-%d %H:%M"))
        time.sleep(max(0.0, (next_run - datetime.now(UTC)).total_seconds()))
        _safe_ingest()


def _safe_ingest() -> None:
    try:
        ingest(source=None, no_ai=False)
    except Exception:  # keep the scheduler alive; the next day retries
        log.exception("ingestion run failed")


@app.command()
def stats() -> None:
    """Show what the site currently publishes."""
    s = build_repository(get_settings()).stats()
    typer.echo(f"eligible jobs: {s.eligible_jobs}\nneeds review: {s.review_jobs}\n"
               f"companies: {s.companies}\nlast refreshed: {s.last_refreshed_at}")


if __name__ == "__main__":
    app()
