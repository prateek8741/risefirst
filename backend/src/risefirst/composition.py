"""Composition root: the one place that wires concrete adapters into use cases."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Engine, create_engine

from risefirst.application.catalog import JobCatalog
from risefirst.application.ingest import IngestJobs
from risefirst.application.ports import Enricher
from risefirst.config import Settings, get_settings
from risefirst.infrastructure.connectors.registry import build_connectors, load_sources
from risefirst.infrastructure.http import PoliteHttpClient
from risefirst.infrastructure.persistence.repository import PostgresJobRepository


@lru_cache
def engine_for(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True, pool_size=5, max_overflow=5)


def build_repository(settings: Settings) -> PostgresJobRepository:
    return PostgresJobRepository(engine_for(settings.database_url))


def build_enricher(settings: Settings, use_ai: bool = True) -> Enricher | None:
    if not (use_ai and settings.ai_enabled and settings.gemini_api_key):
        return None
    from risefirst.infrastructure.llm.gemini import GeminiEnricher  # imported only when used

    return GeminiEnricher(
        settings.gemini_api_key.get_secret_value(), settings.gemini_model, settings.ai_requests_per_minute
    )


def build_ingestion(
    settings: Settings, http: PoliteHttpClient, only: str | None = None, use_ai: bool = True
) -> IngestJobs:
    connectors = build_connectors(load_sources(settings.sources_file), http, only)
    return IngestJobs(
        connectors,
        build_repository(settings),
        build_enricher(settings, use_ai),
        ai_call_budget=settings.ai_call_budget,
        ai_concurrency=settings.ai_concurrency,
    )


def build_catalog(settings: Settings | None = None) -> JobCatalog:
    return JobCatalog(build_repository(settings or get_settings()))
