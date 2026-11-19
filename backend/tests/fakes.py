"""In-memory test doubles for the application ports."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from datetime import UTC, datetime

from risefirst.application.ports import Facets, JobPage, JobQuery, SiteStats
from risefirst.domain.enums import Category, Eligibility, EmploymentType, JobStatus, WorkMode
from risefirst.domain.models import Enrichment, Job, RawPosting, RunReport

NOW = datetime(2026, 11, 19, 6, 0, tzinfo=UTC)


def posting(external_id: str = "1", title: str = "Software Engineering Intern", location: str = "Bengaluru",
            description: str = "Learn and build.", board: str = "acme", company: str = "Acme") -> RawPosting:
    return RawPosting(source="greenhouse", board=board, external_id=external_id, company=company, title=title,
                      location_text=location, description=description,
                      apply_url=f"https://boards.greenhouse.io/{board}/jobs/{external_id}", posted_at=NOW)


class FakeConnector:
    def __init__(self, postings: list[RawPosting], name: str = "greenhouse:acme", error: Exception | None = None):
        self.postings = postings
        self._name = name
        self.error = error

    @property
    def name(self) -> str:
        return self._name

    def fetch(self) -> list[RawPosting]:
        if self.error:
            raise self.error
        return self.postings


class FakeEnricher:
    def __init__(self, fresher: bool = True, confidence: float = 0.9) -> None:
        self.calls: list[str] = []
        self.fresher = fresher
        self.confidence = confidence

    def enrich(self, p: RawPosting) -> Enrichment:
        self.calls.append(p.source_key)
        return Enrichment(category=Category.SOFTWARE, skills=("Python", "SQL"),
                          employment_type=EmploymentType.FULL_TIME, work_mode=WorkMode.ONSITE,
                          experience_min=0, experience_max=1, fresher_friendly=self.fresher,
                          confidence=self.confidence, summary="Builds software.", model="fake")


class InMemoryRepository:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.runs: list[RunReport] = []
        self._next_id = 1

    def find_by_source_keys(self, keys: Iterable[str]) -> dict[str, Job]:
        return {k: self.jobs[k] for k in keys if k in self.jobs}

    def save(self, jobs: list[Job]) -> None:
        for job in jobs:
            if job.id is None:
                job = replace(job, id=self._next_id)
                self._next_id += 1
            self.jobs[job.source_key] = job

    def mark_missing(self, source_name: str, seen_keys: set[str], now: datetime, close_after: int) -> int:
        closed = 0
        for job in self.jobs.values():
            if f"{job.source}:{job.board}" == source_name and job.status is JobStatus.ACTIVE \
                    and job.source_key not in seen_keys:
                job.missed_runs += 1
                if job.missed_runs >= close_after:
                    job.status = JobStatus.CLOSED
                    closed += 1
        return closed

    def refresh_duplicates(self) -> None:
        canonical: dict[str, int] = {}
        for job in sorted(self.jobs.values(), key=lambda j: (j.first_seen_at, j.id or 0)):
            job.duplicate_of = None
            if job.status is JobStatus.ACTIVE and job.eligibility is not Eligibility.REJECTED:
                if job.fingerprint in canonical:
                    job.duplicate_of = canonical[job.fingerprint]
                else:
                    canonical[job.fingerprint] = job.id or 0

    def record_run(self, report: RunReport) -> None:
        self.runs.append(report)

    def visible(self, include_review: bool = False) -> list[Job]:
        allowed = {Eligibility.ELIGIBLE} | ({Eligibility.REVIEW_REQUIRED} if include_review else set())
        return [j for j in self.jobs.values()
                if j.status is JobStatus.ACTIVE and j.duplicate_of is None and j.eligibility in allowed]

    def search(self, query: JobQuery) -> JobPage:
        items = [j for j in self.visible(query.include_review)
                 if (not query.text or query.text.lower() in (j.title + j.company).lower())
                 and (not query.ai_assessed_only or j.ai_model is not None)]
        start = (query.page - 1) * query.page_size
        return JobPage(items[start:start + query.page_size], len(items), query.page, query.page_size)

    def get(self, job_id: int) -> Job | None:
        return next((j for j in self.jobs.values() if j.id == job_id), None)

    def facets(self, query: JobQuery) -> Facets:
        return Facets()

    def stats(self) -> SiteStats:
        ai = sum(1 for j in self.visible(include_review=True) if j.ai_model is not None)
        return SiteStats(len(self.visible()), 0, len({j.company for j in self.visible()}), ai, None)
