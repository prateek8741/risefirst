"""Turns a RawPosting (+ optional AI enrichment) into the Job the site shows."""

from __future__ import annotations

from datetime import datetime

from risefirst.domain.classification import category_of, employment_type_of
from risefirst.domain.eligibility import combine_with_ai, decide_by_rules
from risefirst.domain.enums import EmploymentType, JobStatus, WorkMode
from risefirst.domain.experience import parse_experience
from risefirst.domain.identity import content_hash, fingerprint, slugify
from risefirst.domain.location import cities_in, work_mode_of
from risefirst.domain.models import EligibilityDecision, Enrichment, Job, RawPosting


def posting_content_hash(raw: RawPosting) -> str:
    """Changes only when the parts that affect classification change."""
    return content_hash(raw.title, raw.location_text, raw.description, raw.employment_type_hint or "")


def rules_decision(raw: RawPosting) -> EligibilityDecision:
    return decide_by_rules(raw.title, parse_experience(raw.description))


def build_job(raw: RawPosting, now: datetime, existing: Job | None, enrichment: Enrichment | None) -> Job:
    experience = parse_experience(raw.description)
    decision = combine_with_ai(decide_by_rules(raw.title, experience), enrichment)
    cities = cities_in(raw.location_text)

    employment_type = employment_type_of(raw.title, raw.employment_type_hint)
    work_mode = work_mode_of(raw.location_text, raw.work_mode_hint)
    category = category_of(raw.title)
    skills: list[str] = []
    if enrichment is not None:
        # Rules stay authoritative where they found something; AI fills the gaps.
        if employment_type is EmploymentType.UNKNOWN:
            employment_type = enrichment.employment_type
        if work_mode is WorkMode.UNKNOWN:
            work_mode = enrichment.work_mode
        category = enrichment.category
        skills = list(enrichment.skills)

    return Job(
        id=existing.id if existing else None,
        source_key=raw.source_key,
        source=raw.source,
        board=raw.board,
        company=raw.company,
        title=raw.title.strip(),
        slug=slugify(raw.company, raw.title),
        location_text=raw.location_text,
        cities=cities,
        work_mode=work_mode,
        employment_type=employment_type,
        category=category,
        skills=skills,
        experience_min=experience.min_years if experience.stated else (
            enrichment.experience_min if enrichment else None),
        experience_max=experience.max_years if experience.stated else (
            enrichment.experience_max if enrichment else None),
        eligibility=decision.eligibility,
        eligibility_reason=decision.reason,
        classified_by=decision.classified_by,
        description=raw.description,
        summary=enrichment.summary if enrichment else None,
        apply_url=raw.apply_url,
        posted_at=raw.posted_at,
        fingerprint=fingerprint(raw.company, raw.title, cities),
        content_hash=posting_content_hash(raw),
        first_seen_at=existing.first_seen_at if existing else now,
        last_seen_at=now,
        status=JobStatus.ACTIVE,
        missed_runs=0,
        ai_model=enrichment.model if enrichment else None,
        enrichment=enrichment,
    )
