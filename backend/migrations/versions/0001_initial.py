"""Initial schema: jobs (with full-text search) and ingestion_runs.

Revision ID: 0001
Revises:
Create Date: 2026-11-19
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from risefirst.infrastructure.persistence.tables import SEARCH_VECTOR_SQL

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("source_key", sa.Text, nullable=False, unique=True),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("board", sa.Text, nullable=False),
        sa.Column("company", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("slug", sa.Text, nullable=False),
        sa.Column("location_text", sa.Text, nullable=False, server_default=""),
        sa.Column("cities", postgresql.ARRAY(sa.Text), nullable=False, server_default="{}"),
        sa.Column("work_mode", sa.Text, nullable=False),
        sa.Column("employment_type", sa.Text, nullable=False),
        sa.Column("category", sa.Text, nullable=False),
        sa.Column("skills", postgresql.ARRAY(sa.Text), nullable=False, server_default="{}"),
        sa.Column("skills_text", sa.Text, nullable=False, server_default=""),
        sa.Column("experience_min", sa.Float),
        sa.Column("experience_max", sa.Float),
        sa.Column("eligibility", sa.Text, nullable=False),
        sa.Column("eligibility_reason", sa.Text, nullable=False),
        sa.Column("classified_by", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("summary", sa.Text),
        sa.Column("apply_url", sa.Text, nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True)),
        sa.Column("fingerprint", sa.Text, nullable=False),
        sa.Column("content_hash", sa.Text, nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("missed_runs", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ai_model", sa.Text),
        sa.Column("enrichment", postgresql.JSONB),
        sa.Column("duplicate_of", sa.BigInteger, sa.ForeignKey("jobs.id", ondelete="SET NULL")),
        sa.Column("search_vector", postgresql.TSVECTOR, sa.Computed(SEARCH_VECTOR_SQL, persisted=True)),
        sa.CheckConstraint("eligibility IN ('eligible', 'review_required', 'rejected')", name="ck_jobs_eligibility"),
        sa.CheckConstraint("status IN ('active', 'closed')", name="ck_jobs_status"),
    )
    op.create_index("ix_jobs_listing", "jobs", ["status", "eligibility", "posted_at"])
    op.create_index("ix_jobs_fingerprint", "jobs", ["fingerprint"])
    op.create_index("ix_jobs_source_board", "jobs", ["source", "board"])
    op.create_index("ix_jobs_cities", "jobs", ["cities"], postgresql_using="gin")
    op.create_index("ix_jobs_search", "jobs", ["search_vector"], postgresql_using="gin")

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("report", postgresql.JSONB, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ingestion_runs")
    op.drop_table("jobs")
