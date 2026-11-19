"""PostgreSQL implementation of the JobRepository port."""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import Engine, and_, case, desc, func, literal_column, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert

from risefirst.application.ports import Facets, JobPage, JobQuery, SiteStats
from risefirst.domain.enums import (
    Category,
    ClassifiedBy,
    Eligibility,
    EmploymentType,
    JobStatus,
    WorkMode,
)
from risefirst.domain.models import Enrichment, Job, RunReport
from risefirst.infrastructure.persistence.tables import ingestion_runs, jobs

_WRITABLE = [c.name for c in jobs.columns if c.name not in {"id", "search_vector", "duplicate_of"}]
# On re-ingest these must keep their original values.
_KEEP_ON_UPDATE = {"source_key", "first_seen_at"}


def _enrichment_to_json(enrichment: Enrichment | None) -> dict[str, Any] | None:
    if enrichment is None:
        return None
    data = dataclasses.asdict(enrichment)
    data["skills"] = list(enrichment.skills)
    return data


def _enrichment_from_json(data: dict[str, Any] | None) -> Enrichment | None:
    if not data:
        return None
    try:
        return Enrichment(
            category=Category(data["category"]),
            skills=tuple(data.get("skills") or ()),
            employment_type=EmploymentType(data["employment_type"]),
            work_mode=WorkMode(data["work_mode"]),
            experience_min=data.get("experience_min"),
            experience_max=data.get("experience_max"),
            fresher_friendly=bool(data["fresher_friendly"]),
            confidence=float(data["confidence"]),
            summary=data.get("summary") or "",
            model=data.get("model") or "",
        )
    except (KeyError, ValueError):
        return None  # stored by an older schema: treat as not enriched


def _row_to_job(row: Any) -> Job:
    m = row._mapping
    return Job(
        id=m["id"],
        source_key=m["source_key"],
        source=m["source"],
        board=m["board"],
        company=m["company"],
        title=m["title"],
        slug=m["slug"],
        location_text=m["location_text"],
        cities=list(m["cities"] or []),
        work_mode=WorkMode(m["work_mode"]),
        employment_type=EmploymentType(m["employment_type"]),
        category=Category(m["category"]),
        skills=list(m["skills"] or []),
        experience_min=m["experience_min"],
        experience_max=m["experience_max"],
        eligibility=Eligibility(m["eligibility"]),
        eligibility_reason=m["eligibility_reason"],
        classified_by=ClassifiedBy(m["classified_by"]),
        description=m["description"],
        summary=m["summary"],
        apply_url=m["apply_url"],
        posted_at=m["posted_at"],
        fingerprint=m["fingerprint"],
        content_hash=m["content_hash"],
        first_seen_at=m["first_seen_at"],
        last_seen_at=m["last_seen_at"],
        status=JobStatus(m["status"]),
        missed_runs=m["missed_runs"],
        ai_model=m["ai_model"],
        enrichment=_enrichment_from_json(m["enrichment"]),
        duplicate_of=m["duplicate_of"],
    )


def _job_to_row(job: Job) -> dict[str, Any]:
    row = {
        "source_key": job.source_key,
        "source": job.source,
        "board": job.board,
        "company": job.company,
        "title": job.title,
        "slug": job.slug,
        "location_text": job.location_text,
        "cities": job.cities,
        "work_mode": job.work_mode.value,
        "employment_type": job.employment_type.value,
        "category": job.category.value,
        "skills": job.skills,
        "skills_text": " ".join(job.skills),
        "experience_min": job.experience_min,
        "experience_max": job.experience_max,
        "eligibility": job.eligibility.value,
        "eligibility_reason": job.eligibility_reason,
        "classified_by": job.classified_by.value,
        "description": job.description,
        "summary": job.summary,
        "apply_url": job.apply_url,
        "posted_at": job.posted_at,
        "fingerprint": job.fingerprint,
        "content_hash": job.content_hash,
        "first_seen_at": job.first_seen_at,
        "last_seen_at": job.last_seen_at,
        "status": job.status.value,
        "missed_runs": job.missed_runs,
        "ai_model": job.ai_model,
        "enrichment": _enrichment_to_json(job.enrichment),
    }
    assert set(row) == set(_WRITABLE), "job row out of sync with table"
    return row


class PostgresJobRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    # ---- write side (ingestion) ----

    def find_by_source_keys(self, keys: Iterable[str]) -> dict[str, Job]:
        key_list = list(keys)
        if not key_list:
            return {}
        with self._engine.connect() as conn:
            rows = conn.execute(select(jobs).where(jobs.c.source_key.in_(key_list)))
            return {row.source_key: _row_to_job(row) for row in rows}

    def save(self, job_list: list[Job]) -> None:
        if not job_list:
            return
        statement = insert(jobs).values([_job_to_row(j) for j in job_list])
        statement = statement.on_conflict_do_update(
            index_elements=[jobs.c.source_key],
            set_={name: statement.excluded[name] for name in _WRITABLE if name not in _KEEP_ON_UPDATE},
        )
        with self._engine.begin() as conn:
            conn.execute(statement)

    def mark_missing(self, source_name: str, seen_keys: set[str], now: datetime, close_after: int) -> int:
        source, board = source_name.split(":", 1)
        in_source = and_(jobs.c.source == source, jobs.c.board == board, jobs.c.status == JobStatus.ACTIVE)
        unseen = ~jobs.c.source_key.in_(list(seen_keys)) if seen_keys else literal_column("true")
        with self._engine.begin() as conn:
            conn.execute(update(jobs).where(in_source, unseen).values(missed_runs=jobs.c.missed_runs + 1))
            closed = conn.execute(
                update(jobs)
                .where(in_source, jobs.c.missed_runs >= close_after)
                .values(status=JobStatus.CLOSED.value)
            )
            return closed.rowcount or 0

    def refresh_duplicates(self) -> None:
        with self._engine.begin() as conn:
            conn.execute(update(jobs).where(jobs.c.duplicate_of.is_not(None)).values(duplicate_of=None))
            conn.execute(text("""
                UPDATE jobs AS j SET duplicate_of = d.canonical_id
                FROM (
                    SELECT id, first_value(id) OVER (
                        PARTITION BY fingerprint
                        ORDER BY (eligibility = 'eligible') DESC, first_seen_at, id
                    ) AS canonical_id
                    FROM jobs
                    WHERE status = 'active' AND eligibility <> 'rejected'
                ) AS d
                WHERE j.id = d.id AND d.canonical_id <> j.id
            """))

    def record_run(self, report: RunReport) -> None:
        payload = dataclasses.asdict(report)
        payload["started_at"] = report.started_at.isoformat()
        payload["finished_at"] = report.finished_at.isoformat() if report.finished_at else None
        with self._engine.begin() as conn:
            conn.execute(ingestion_runs.insert().values(
                started_at=report.started_at, finished_at=report.finished_at, report=payload))

    # ---- read side (public API) ----

    @staticmethod
    def _visible(include_review: bool) -> list[Any]:
        allowed = [Eligibility.ELIGIBLE.value]
        if include_review:
            allowed.append(Eligibility.REVIEW_REQUIRED.value)
        return [
            jobs.c.status == JobStatus.ACTIVE.value,
            jobs.c.duplicate_of.is_(None),
            jobs.c.eligibility.in_(allowed),
        ]

    @classmethod
    def _conditions(cls, query: JobQuery, skip: str | None = None) -> list[Any]:
        """WHERE clauses for a query. `skip` leaves out one dropdown filter, so that dropdown's
        counts show what each of its options would return given everything else selected."""
        conditions = cls._visible(query.include_review)
        if query.text:
            tsquery = func.websearch_to_tsquery("english", query.text)
            like = "%" + query.text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            conditions.append(or_(
                jobs.c.search_vector.op("@@")(tsquery),
                jobs.c.title.ilike(like, escape="\\"),
                jobs.c.company.ilike(like, escape="\\"),
            ))
        if query.category and skip != "category":
            conditions.append(jobs.c.category == query.category.value)
        if query.city and skip != "city":
            conditions.append(jobs.c.cities.contains([query.city]))
        if query.employment_type and skip != "employment_type":
            conditions.append(jobs.c.employment_type == query.employment_type.value)
        if query.work_mode and skip != "work_mode":
            conditions.append(jobs.c.work_mode == query.work_mode.value)
        if query.ai_assessed_only:
            conditions.append(jobs.c.ai_model.is_not(None))
        return conditions

    def search(self, query: JobQuery) -> JobPage:
        conditions = self._conditions(query)
        rank = None
        if query.text:
            rank = func.ts_rank(jobs.c.search_vector, func.websearch_to_tsquery("english", query.text))

        # Verified fresher roles first, then newest.
        order = [case((jobs.c.eligibility == Eligibility.ELIGIBLE.value, 0), else_=1)]
        if rank is not None:
            order.append(desc(rank))
        order += [jobs.c.posted_at.desc().nulls_last(), jobs.c.id.desc()]

        with self._engine.connect() as conn:
            total = conn.execute(select(func.count()).select_from(jobs).where(*conditions)).scalar_one()
            rows = conn.execute(
                select(jobs).where(*conditions).order_by(*order)
                .limit(query.page_size).offset((query.page - 1) * query.page_size)
            )
            items = [_row_to_job(row) for row in rows]
        return JobPage(items=items, total=total, page=query.page, page_size=query.page_size)

    def get(self, job_id: int) -> Job | None:
        with self._engine.connect() as conn:
            row = conn.execute(select(jobs).where(jobs.c.id == job_id)).first()
            return _row_to_job(row) if row else None

    def facets(self, query: JobQuery) -> Facets:
        with self._engine.connect() as conn:
            def counts(column: Any, skip: str) -> dict[str, int]:
                rows = conn.execute(
                    select(column, func.count()).where(*self._conditions(query, skip))
                    .group_by(column).order_by(func.count().desc(), column))
                return {str(value): count for value, count in rows if value is not None}

            city = func.unnest(jobs.c.cities).label("city")
            city_rows = conn.execute(
                select(city, func.count()).where(*self._conditions(query, "city"))
                .group_by(literal_column("city")).order_by(func.count().desc(), literal_column("city"))
            )
            return Facets(
                categories=counts(jobs.c.category, "category"),
                cities={value: count for value, count in city_rows},
                employment_types=counts(jobs.c.employment_type, "employment_type"),
                work_modes=counts(jobs.c.work_mode, "work_mode"),
            )

    def stats(self) -> SiteStats:
        active = and_(jobs.c.status == JobStatus.ACTIVE.value, jobs.c.duplicate_of.is_(None))
        with self._engine.connect() as conn:
            row = conn.execute(select(
                func.count().filter(jobs.c.eligibility == Eligibility.ELIGIBLE.value),
                func.count().filter(jobs.c.eligibility == Eligibility.REVIEW_REQUIRED.value),
                func.count(func.distinct(jobs.c.company)).filter(
                    jobs.c.eligibility == Eligibility.ELIGIBLE.value),
                func.count().filter(
                    jobs.c.ai_model.is_not(None), jobs.c.eligibility != Eligibility.REJECTED.value),
            ).where(active)).one()
            last = conn.execute(select(func.max(ingestion_runs.c.finished_at))).scalar_one()
        return SiteStats(eligible_jobs=row[0], review_jobs=row[1], companies=row[2], ai_assessed_jobs=row[3],
                         last_refreshed_at=last)
