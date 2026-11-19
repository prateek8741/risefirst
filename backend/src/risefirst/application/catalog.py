"""Read-side use cases for the public site. Thin today; the seam for caching or ranking later."""

from __future__ import annotations

from dataclasses import replace

from risefirst.application.ports import Facets, JobPage, JobQuery, JobRepository, SiteStats
from risefirst.domain.enums import Eligibility, JobStatus
from risefirst.domain.models import Job

MAX_PAGE_SIZE = 50


def _normalize(query: JobQuery) -> JobQuery:
    """One place for query rules, so results and dropdown counts always agree."""
    return replace(
        query,
        text=(query.text or "").strip()[:200] or None,
        city=(query.city or "").strip() or None,
        # "Show me what the AI looked at" means all of it, including jobs it left unclear,
        # so the filter matches the "N assessed by AI" count on the site.
        include_review=query.include_review or query.ai_assessed_only,
        page=max(query.page, 1),
        page_size=min(max(query.page_size, 1), MAX_PAGE_SIZE),
    )


class JobCatalog:
    def __init__(self, repository: JobRepository) -> None:
        self._repository = repository

    def search(self, query: JobQuery) -> JobPage:
        return self._repository.search(_normalize(query))

    def facets(self, query: JobQuery) -> Facets:
        return self._repository.facets(_normalize(query))

    def get(self, job_id: int) -> Job | None:
        """Only jobs the public site may show: active and not rejected."""
        job = self._repository.get(job_id)
        if job is None or job.status is not JobStatus.ACTIVE or job.eligibility is Eligibility.REJECTED:
            return None
        return job

    def stats(self) -> SiteStats:
        return self._repository.stats()
