"""Store "no AI result" as SQL NULL instead of JSON null.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-19
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE jobs SET enrichment = NULL WHERE enrichment = 'null'::jsonb")


def downgrade() -> None:
    pass  # nothing to restore: both forms meant "not enriched"
