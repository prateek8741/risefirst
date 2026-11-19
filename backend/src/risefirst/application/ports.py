"""Interfaces the application layer needs. Infrastructure implements them; tests fake them."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from risefirst.domain.enums import Category, EmploymentType, WorkMode
from risefirst.domain.models import Enrichment, Job, RawPosting, RunReport


class SourceConnector(Protocol):
    @property
    def name(self) -> str:
        """Unique source name, e.g. 'greenhouse:stripe'."""
        ...

    def fetch(self) -> list[RawPosting]:
        """All currently open postings. Raises on failure (the run then skips this source)."""
        ...


class EnricherUnavailable(Exception):  # noqa: N818 - reads better at the raise site
    """The AI provider cannot take more calls this run (e.g. daily quota used up)."""


class Enricher(Protocol):
    def enrich(self, posting: RawPosting) -> Enrichment | None:
        """Structured fields for one posting, or None if the model could not produce them.
        Raises EnricherUnavailable when no further calls should be made this run."""
        ...


@dataclass(frozen=True)
class JobQuery:
    text: str | None = None
    category: Category | None = None
    city: str | None = None
    employment_type: EmploymentType | None = None
    work_mode: WorkMode | None = None
    include_review: bool = False
    ai_assessed_only: bool = False
    page: int = 1
    page_size: int = 20


@dataclass(frozen=True)
class JobPage:
    items: list[Job]
    total: int
    page: int
    page_size: int


@dataclass(frozen=True)
class Facets:
    categories: dict[str, int] = field(default_factory=dict)
    cities: dict[str, int] = field(default_factory=dict)
    employment_types: dict[str, int] = field(default_factory=dict)
    work_modes: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class SiteStats:
    eligible_jobs: int
    review_jobs: int
    companies: int
    ai_assessed_jobs: int  # published or review jobs that Gemini has read
    last_refreshed_at: datetime | None


class JobRepository(Protocol):
    def find_by_source_keys(self, keys: Iterable[str]) -> dict[str, Job]: ...

    def save(self, jobs: list[Job]) -> None:
        """Insert or update by source_key."""
        ...

    def mark_missing(self, source_name: str, seen_keys: set[str], now: datetime, close_after: int) -> int:
        """Bump the miss counter of active jobs of this source not seen now; close those at
        `close_after` misses. Returns how many were closed."""
        ...

    def refresh_duplicates(self) -> None:
        """Among active jobs sharing a fingerprint, keep the oldest; mark the rest duplicates."""
        ...

    def record_run(self, report: RunReport) -> None: ...

    def search(self, query: JobQuery) -> JobPage: ...

    def get(self, job_id: int) -> Job | None: ...

    def facets(self, query: JobQuery) -> Facets:
        """Option counts per dropdown, given every other active filter."""
        ...

    def stats(self) -> SiteStats: ...
