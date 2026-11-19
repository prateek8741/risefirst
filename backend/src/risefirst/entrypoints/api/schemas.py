"""Public API response models (the JSON contract the web app depends on)."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel

from risefirst.domain.models import Job

# Some employers paste bullets from Word's Symbol font: private-use code points that render as
# empty boxes in normal fonts. Shown as "•" here; the stored text is untouched (no AI re-runs).
_PRIVATE_USE = re.compile("[\ue000-\uf8ff]")


def display_text(text: str) -> str:
    return _PRIVATE_USE.sub("•", text)


class JobSummary(BaseModel):
    id: int
    slug: str
    title: str
    company: str
    location: str
    cities: list[str]
    work_mode: str
    employment_type: str
    category: str
    skills: list[str]
    experience_min: float | None
    experience_max: float | None
    verified_fresher: bool  # False = shown only with "include unverified"
    ai_assessed: bool  # Gemini read this posting (skills, summary, and possibly the decision)
    decided_by_ai: bool  # the fresher/not-fresher decision itself came from the AI
    summary: str | None
    posted_at: datetime | None
    last_verified_at: datetime
    source: str

    @classmethod
    def from_job(cls, job: Job) -> JobSummary:
        assert job.id is not None
        return cls(
            id=job.id,
            slug=job.slug,
            title=job.title,
            company=job.company,
            location=job.location_text,
            cities=job.cities,
            work_mode=job.work_mode.value,
            employment_type=job.employment_type.value,
            category=job.category.value,
            skills=job.skills,
            experience_min=job.experience_min,
            experience_max=job.experience_max,
            verified_fresher=job.eligibility.value == "eligible",
            ai_assessed=job.ai_model is not None,
            decided_by_ai=job.classified_by.value == "ai",
            summary=job.summary,
            posted_at=job.posted_at,
            last_verified_at=job.last_seen_at,
            source=job.source.capitalize(),
        )


class JobDetail(JobSummary):
    description: str
    apply_url: str
    eligibility_reason: str
    classified_by: str

    @classmethod
    def from_job(cls, job: Job) -> JobDetail:
        return cls(
            **JobSummary.from_job(job).model_dump(),
            description=display_text(job.description),
            apply_url=job.apply_url,
            eligibility_reason=job.eligibility_reason,
            classified_by=job.classified_by.value,
        )


class JobList(BaseModel):
    items: list[JobSummary]
    total: int
    page: int
    page_size: int
    pages: int


class FacetsOut(BaseModel):
    categories: dict[str, int]
    cities: dict[str, int]
    employment_types: dict[str, int]
    work_modes: dict[str, int]


class StatsOut(BaseModel):
    eligible_jobs: int
    review_jobs: int
    ai_assessed_jobs: int
    companies: int
    last_refreshed_at: datetime | None
