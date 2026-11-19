"""Use case: refresh the job catalogue from every configured source."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from risefirst.application.ports import Enricher, EnricherUnavailable, JobRepository, SourceConnector
from risefirst.domain.enums import Eligibility
from risefirst.domain.job_builder import build_job, posting_content_hash, rules_decision
from risefirst.domain.location import is_in_india
from risefirst.domain.models import Enrichment, Job, RawPosting, RunReport

log = logging.getLogger(__name__)

# A job disappears from its board -> closed after this many consecutive successful runs
# without it. One miss could be a board glitch; two is a pattern.
CLOSE_AFTER_MISSES = 2


def _utcnow() -> datetime:
    return datetime.now(UTC)


class IngestJobs:
    def __init__(
        self,
        connectors: Sequence[SourceConnector],
        repository: JobRepository,
        enricher: Enricher | None = None,
        *,
        ai_call_budget: int = 300,
        ai_concurrency: int = 4,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._connectors = connectors
        self._repository = repository
        self._enricher = enricher
        self._ai_budget = ai_call_budget
        self._ai_concurrency = ai_concurrency
        self._clock = clock
        self._ai_stopped = False

    def run(self) -> RunReport:
        self._ai_stopped = False
        report = RunReport(started_at=self._clock())
        for connector in self._connectors:
            try:
                postings = connector.fetch()
            except Exception as error:  # one broken source must not stop the others
                log.warning("source %s failed: %s", connector.name, error)
                report.sources_failed[connector.name] = str(error)[:300]
                continue
            self._ingest_source(connector.name, postings, report)
            report.sources_ok.append(connector.name)

        self._repository.refresh_duplicates()
        report.finished_at = self._clock()
        self._repository.record_run(report)
        return report

    def _ingest_source(self, source_name: str, postings: list[RawPosting], report: RunReport) -> None:
        now = self._clock()
        report.fetched += len(postings)
        india = [p for p in postings if is_in_india(p.location_text)]
        report.india += len(india)

        existing = self._repository.find_by_source_keys(p.source_key for p in india)
        enrichments = self._enrich(india, existing, report)

        jobs: list[Job] = []
        for posting in india:
            previous = existing.get(posting.source_key)
            job = build_job(posting, now, previous, enrichments.get(posting.source_key))
            jobs.append(job)
            if previous is None:
                report.new += 1
            elif previous.content_hash != job.content_hash:
                report.updated += 1
            match job.eligibility:
                case Eligibility.ELIGIBLE:
                    report.eligible += 1
                case Eligibility.REVIEW_REQUIRED:
                    report.review_required += 1
                case Eligibility.REJECTED:
                    report.rejected += 1

        self._repository.save(jobs)
        seen = {p.source_key for p in india}
        report.closed += self._repository.mark_missing(source_name, seen, now, CLOSE_AFTER_MISSES)

    def _enrich(
        self, postings: list[RawPosting], existing: dict[str, Job], report: RunReport
    ) -> dict[str, Enrichment]:
        """AI only for postings the rules did not reject, and only when their text changed."""
        result: dict[str, Enrichment] = {}
        to_call: list[RawPosting] = []
        for posting in postings:
            if rules_decision(posting).eligibility is Eligibility.REJECTED:
                continue
            previous = existing.get(posting.source_key)
            if previous and previous.enrichment and previous.content_hash == posting_content_hash(posting):
                result[posting.source_key] = previous.enrichment
                report.ai_cache_hits += 1
            elif self._enricher is not None:
                to_call.append(posting)

        remaining = max(0, self._ai_budget - report.ai_calls)
        report.ai_skipped += max(0, len(to_call) - remaining)
        to_call = to_call[:remaining]
        if self._ai_stopped:
            report.ai_skipped += len(to_call)
            return result
        if not to_call or self._enricher is None:
            return result

        enricher = self._enricher

        def call(posting: RawPosting) -> tuple[str, Enrichment | None, bool]:
            """Returns (key, enrichment, attempted)."""
            if self._ai_stopped:
                return posting.source_key, None, False
            try:
                return posting.source_key, enricher.enrich(posting), True
            except EnricherUnavailable as error:
                if not self._ai_stopped:
                    log.warning("AI paused for the rest of this run: %s", error)
                self._ai_stopped = True
                return posting.source_key, None, True
            except Exception as error:
                log.warning("AI enrichment failed for %s: %s", posting.source_key, str(error)[:200])
                return posting.source_key, None, True

        with ThreadPoolExecutor(max_workers=self._ai_concurrency) as pool:
            for key, enrichment, attempted in pool.map(call, to_call):
                if not attempted:
                    report.ai_skipped += 1
                    continue
                report.ai_calls += 1
                if enrichment is None:
                    report.ai_failures += 1
                else:
                    result[key] = enrichment
        return result
