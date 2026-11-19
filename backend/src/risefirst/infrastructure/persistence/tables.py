"""PostgreSQL schema (SQLAlchemy Core). Migrations in backend/migrations mirror this."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Column,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR

metadata = MetaData()

SEARCH_VECTOR_SQL = (
    "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('english', coalesce(company, '')), 'A') || "
    "setweight(to_tsvector('english', coalesce(skills_text, '')), 'B') || "
    "setweight(to_tsvector('english', coalesce(summary, '')), 'C') || "
    "setweight(to_tsvector('english', coalesce(description, '')), 'D')"
)

jobs = Table(
    "jobs",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("source_key", Text, nullable=False, unique=True),
    Column("source", Text, nullable=False),
    Column("board", Text, nullable=False),
    Column("company", Text, nullable=False),
    Column("title", Text, nullable=False),
    Column("slug", Text, nullable=False),
    Column("location_text", Text, nullable=False, server_default=""),
    Column("cities", ARRAY(Text), nullable=False, server_default="{}"),
    Column("work_mode", Text, nullable=False),
    Column("employment_type", Text, nullable=False),
    Column("category", Text, nullable=False),
    Column("skills", ARRAY(Text), nullable=False, server_default="{}"),
    Column("skills_text", Text, nullable=False, server_default=""),
    Column("experience_min", Float),
    Column("experience_max", Float),
    Column("eligibility", Text, nullable=False),
    Column("eligibility_reason", Text, nullable=False),
    Column("classified_by", Text, nullable=False),
    Column("description", Text, nullable=False),
    Column("summary", Text),
    Column("apply_url", Text, nullable=False),
    Column("posted_at", DateTime(timezone=True)),
    Column("fingerprint", Text, nullable=False),
    Column("content_hash", Text, nullable=False),
    Column("first_seen_at", DateTime(timezone=True), nullable=False),
    Column("last_seen_at", DateTime(timezone=True), nullable=False),
    Column("status", Text, nullable=False),
    Column("missed_runs", Integer, nullable=False, server_default="0"),
    Column("ai_model", Text),
    Column("enrichment", JSONB(none_as_null=True)),
    Column("duplicate_of", BigInteger, ForeignKey("jobs.id", ondelete="SET NULL")),
    Column("search_vector", TSVECTOR, Computed(SEARCH_VECTOR_SQL, persisted=True)),
    Index("ix_jobs_listing", "status", "eligibility", "posted_at"),
    Index("ix_jobs_fingerprint", "fingerprint"),
    Index("ix_jobs_source_board", "source", "board"),
    Index("ix_jobs_cities", "cities", postgresql_using="gin"),
    Index("ix_jobs_search", "search_vector", postgresql_using="gin"),
)

ingestion_runs = Table(
    "ingestion_runs",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True)),
    Column("report", JSONB, nullable=False),
)
