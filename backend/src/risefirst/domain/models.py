"""Domain entities and value objects. Pure Python: no framework imports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from risefirst.domain.enums import (
    Category,
    ClassifiedBy,
    Eligibility,
    EmploymentType,
    JobStatus,
    WorkMode,
)


@dataclass(frozen=True)
class RawPosting:
    """A job exactly as one source reported it, before any interpretation."""

    source: str  # ATS name, e.g. "greenhouse"
    board: str  # the employer's board slug on that ATS, e.g. "stripe"
    external_id: str
    company: str
    title: str
    location_text: str
    description: str  # plain text
    apply_url: str
    posted_at: datetime | None = None
    employment_type_hint: str | None = None  # the source's own field, if any
    work_mode_hint: str | None = None

    @property
    def source_key(self) -> str:
        """Stable identity of this posting within its source."""
        return f"{self.source}:{self.board}:{self.external_id}"

    @property
    def source_name(self) -> str:
        return f"{self.source}:{self.board}"


@dataclass(frozen=True)
class ExperienceRange:
    """Years of experience a posting asks for, as stated in its text."""

    min_years: float | None = None
    max_years: float | None = None
    freshers_mentioned: bool = False

    @property
    def stated(self) -> bool:
        return self.min_years is not None


@dataclass(frozen=True)
class EligibilityDecision:
    eligibility: Eligibility
    reason: str
    classified_by: ClassifiedBy = ClassifiedBy.RULES


@dataclass(frozen=True)
class Enrichment:
    """Structured fields an AI model extracted from a posting."""

    category: Category
    skills: tuple[str, ...]
    employment_type: EmploymentType
    work_mode: WorkMode
    experience_min: float | None
    experience_max: float | None
    fresher_friendly: bool
    confidence: float  # 0..1, the model's confidence in its fresher_friendly judgement
    summary: str
    model: str


@dataclass
class Job:
    """A posting after interpretation: what the website shows."""

    source_key: str
    source: str
    board: str
    company: str
    title: str
    slug: str
    location_text: str
    cities: list[str]
    work_mode: WorkMode
    employment_type: EmploymentType
    category: Category
    skills: list[str]
    experience_min: float | None
    experience_max: float | None
    eligibility: Eligibility
    eligibility_reason: str
    classified_by: ClassifiedBy
    description: str
    summary: str | None
    apply_url: str
    posted_at: datetime | None
    fingerprint: str
    content_hash: str
    first_seen_at: datetime
    last_seen_at: datetime
    status: JobStatus = JobStatus.ACTIVE
    missed_runs: int = 0
    ai_model: str | None = None
    enrichment: Enrichment | None = None  # kept so unchanged postings are not re-sent to the AI
    duplicate_of: int | None = None
    id: int | None = None


@dataclass
class RunReport:
    """What one ingestion run did. Stored for observability."""

    started_at: datetime
    finished_at: datetime | None = None
    sources_ok: list[str] = field(default_factory=list)
    sources_failed: dict[str, str] = field(default_factory=dict)
    fetched: int = 0
    india: int = 0
    new: int = 0
    updated: int = 0
    closed: int = 0
    eligible: int = 0
    review_required: int = 0
    rejected: int = 0
    ai_calls: int = 0
    ai_cache_hits: int = 0
    ai_failures: int = 0
    ai_skipped: int = 0  # wanted AI but not called (budget or quota); retried next run
