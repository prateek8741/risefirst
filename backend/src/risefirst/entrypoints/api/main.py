"""FastAPI app: the read-only public API the website calls."""

from __future__ import annotations

import math
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from risefirst.application.catalog import JobCatalog
from risefirst.application.ports import JobQuery
from risefirst.composition import build_catalog
from risefirst.config import get_settings
from risefirst.domain.enums import Category, EmploymentType, WorkMode
from risefirst.entrypoints.api.schemas import FacetsOut, JobDetail, JobList, JobSummary, StatsOut

app = FastAPI(
    title="RiseFirst API",
    version="0.1.0",
    description="Fresher and internship jobs in India, collected daily from employers' own job boards.",
)
app.add_middleware(
    CORSMiddleware, allow_origins=get_settings().cors_origins, allow_methods=["GET"], allow_headers=["*"]
)


def get_catalog() -> JobCatalog:
    return build_catalog()


CatalogDep = Annotated[JobCatalog, Depends(get_catalog)]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def job_query(
    q: Annotated[str | None, Query(max_length=200, description="Search title, company, skills")] = None,
    category: Category | None = None,
    city: Annotated[str | None, Query(max_length=60)] = None,
    employment_type: EmploymentType | None = None,
    work_mode: WorkMode | None = None,
    include_review: Annotated[bool, Query(description="Also show roles whose fresher fit is unverified")] = False,
    ai_assessed: Annotated[bool, Query(description="Only jobs the AI has read (includes unverified ones)")] = False,
    page: Annotated[int, Query(ge=1, le=1000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> JobQuery:
    """The same filter parameters drive /api/jobs and /api/facets, so their counts agree."""
    return JobQuery(
        text=q, category=category, city=city, employment_type=employment_type, work_mode=work_mode,
        include_review=include_review, ai_assessed_only=ai_assessed, page=page, page_size=page_size,
    )


QueryDep = Annotated[JobQuery, Depends(job_query)]


@app.get("/api/jobs", response_model=JobList)
def list_jobs(catalog: CatalogDep, query: QueryDep) -> JobList:
    result = catalog.search(query)
    return JobList(
        items=[JobSummary.from_job(job) for job in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        pages=max(1, math.ceil(result.total / result.page_size)),
    )


@app.get("/api/jobs/{job_id}", response_model=JobDetail)
def get_job(job_id: int, catalog: CatalogDep) -> JobDetail:
    job = catalog.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found or no longer open")
    return JobDetail.from_job(job)


@app.get("/api/facets", response_model=FacetsOut)
def facets(catalog: CatalogDep, query: QueryDep) -> FacetsOut:
    """Counts per dropdown option, given all the other active filters and the search text."""
    f = catalog.facets(query)
    return FacetsOut(categories=f.categories, cities=f.cities,
                     employment_types=f.employment_types, work_modes=f.work_modes)


@app.get("/api/stats", response_model=StatsOut)
def stats(catalog: CatalogDep) -> StatsOut:
    s = catalog.stats()
    return StatsOut(eligible_jobs=s.eligible_jobs, review_jobs=s.review_jobs, companies=s.companies,
                    ai_assessed_jobs=s.ai_assessed_jobs, last_refreshed_at=s.last_refreshed_at)
