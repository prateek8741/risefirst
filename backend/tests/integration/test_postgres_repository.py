"""Runs the real repository against PostgreSQL. Skipped when TEST_DATABASE_URL is unreachable.

Default: postgresql+psycopg://localhost:5432/risefirst_test (create it with `createdb risefirst_test`).
"""

import dataclasses
import os
from datetime import timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from risefirst.application.ingest import IngestJobs
from risefirst.application.ports import JobQuery
from risefirst.domain.enums import Category, JobStatus
from risefirst.infrastructure.persistence.repository import PostgresJobRepository
from risefirst.infrastructure.persistence.tables import metadata
from tests.fakes import NOW, FakeConnector, FakeEnricher, posting

URL = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://localhost:5432/risefirst_test")


@pytest.fixture
def repo():
    engine = create_engine(URL)
    try:
        with engine.connect():
            pass
    except OperationalError:
        pytest.skip("test database not available")
    metadata.drop_all(engine)
    metadata.create_all(engine)
    yield PostgresJobRepository(engine)
    metadata.drop_all(engine)
    engine.dispose()


def ingest(repo, postings, enricher=None, now=NOW):
    return IngestJobs([FakeConnector(postings)], repo, enricher, clock=lambda: now).run()


def test_upsert_is_idempotent_and_keeps_first_seen(repo) -> None:
    ingest(repo, [posting("1")])
    ingest(repo, [posting("1")], now=NOW + timedelta(days=1))
    page = repo.search(JobQuery())
    assert page.total == 1
    assert page.items[0].first_seen_at == NOW
    assert page.items[0].last_seen_at == NOW + timedelta(days=1)


def test_full_text_search_and_filters(repo) -> None:
    ingest(repo, [
        posting("1", "Data Analyst Intern", "Pune", "Work with SQL and Python dashboards."),
        posting("2", "Marketing Intern", "Bengaluru", "Social media campaigns."),
    ])
    assert [j.title for j in repo.search(JobQuery(text="python")).items] == ["Data Analyst Intern"]
    assert [j.title for j in repo.search(JobQuery(text="Marketing")).items] == ["Marketing Intern"]
    assert repo.search(JobQuery(city="Pune")).total == 1
    assert repo.search(JobQuery(category=Category.DATA_AI)).total == 1
    assert repo.search(JobQuery(text="100%_odd\\input")).total == 0  # LIKE wildcards escaped


def test_closing_duplicates_and_facets(repo) -> None:
    ingest(repo, [posting("1", "Data Intern"), posting("2", "Data Intern"), posting("3", "HR Intern")])
    assert repo.search(JobQuery()).total == 2  # the duplicate is hidden
    ingest(repo, [posting("1", "Data Intern")])
    ingest(repo, [posting("1", "Data Intern")])
    assert repo.find_by_source_keys(["greenhouse:acme:3"])["greenhouse:acme:3"].status is JobStatus.CLOSED
    facets = repo.facets(JobQuery())
    assert facets.cities == {"Bengaluru": 1}
    stats = repo.stats()
    assert stats.eligible_jobs == 1 and stats.last_refreshed_at is not None


def test_enrichment_round_trips(repo) -> None:
    ingest(repo, [posting("1", "Analyst", description="Join us.")], FakeEnricher())
    job = repo.find_by_source_keys(["greenhouse:acme:1"])["greenhouse:acme:1"]
    assert job.enrichment is not None and job.enrichment.skills == ("Python", "SQL")
    with repo._engine.connect() as conn:
        assert conn.execute(text("select skills_text from jobs")).scalar_one() == "Python SQL"


def test_facet_counts_always_match_results(repo) -> None:
    """Every dropdown option's count equals what selecting it returns, under any other filters."""
    from itertools import product

    from risefirst.application.catalog import JobCatalog
    from risefirst.domain.enums import EmploymentType, WorkMode

    ingest(repo, [
        posting("1", "Data Analyst Intern", "Pune", "SQL and Python."),
        posting("2", "Marketing Intern", "Bengaluru (Remote)", "Social media."),
        posting("3", "Software Engineering Intern", "Bengaluru | Pune", "Python services."),
        posting("4", "Analyst", "Mumbai", "Join us."),  # unclear experience
        posting("5", "HR Intern", "Hyderabad (Hybrid)", "Recruiting."),
    ], FakeEnricher(fresher=True, confidence=0.5))
    catalog = JobCatalog(repo)
    setters = {
        "category": lambda v: Category(v), "city": lambda v: v,
        "employment_type": lambda v: EmploymentType(v), "work_mode": lambda v: WorkMode(v),
    }
    facet_field = {"category": "categories", "city": "cities", "employment_type": "employment_types",
                   "work_mode": "work_modes"}
    combos = product([None, "python"], [False, True], [False, True], [None, "Pune"])
    for search_text, include_review, ai_only, city in combos:
        base = JobQuery(text=search_text, include_review=include_review, ai_assessed_only=ai_only, city=city)
        facets = catalog.facets(base)
        for dimension, field in facet_field.items():
            for value, count in getattr(facets, field).items():
                selected = dataclasses.replace(base, **{dimension: setters[dimension](value)})
                assert catalog.search(selected).total == count, (base, dimension, value)
