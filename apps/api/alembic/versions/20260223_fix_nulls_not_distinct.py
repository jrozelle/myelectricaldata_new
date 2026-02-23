"""Fix unique constraints to use NULLS NOT DISTINCT

For daily records, interval_start is NULL. PostgreSQL treats NULLs as distinct
in unique constraints by default, which means ON CONFLICT never fires for daily
records and duplicates can be inserted. This migration recreates the constraints
with NULLS NOT DISTINCT (PostgreSQL 15+).

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Recreate consumption_data unique constraint with NULLS NOT DISTINCT
    op.execute("ALTER TABLE consumption_data DROP CONSTRAINT IF EXISTS uq_consumption_data")
    op.execute("""
        ALTER TABLE consumption_data
        ADD CONSTRAINT uq_consumption_data
        UNIQUE NULLS NOT DISTINCT (usage_point_id, date, granularity, interval_start)
    """)

    # Recreate production_data unique constraint with NULLS NOT DISTINCT
    op.execute("ALTER TABLE production_data DROP CONSTRAINT IF EXISTS uq_production_data")
    op.execute("""
        ALTER TABLE production_data
        ADD CONSTRAINT uq_production_data
        UNIQUE NULLS NOT DISTINCT (usage_point_id, date, granularity, interval_start)
    """)


def downgrade() -> None:
    # Revert to standard unique constraints
    op.execute("ALTER TABLE consumption_data DROP CONSTRAINT IF EXISTS uq_consumption_data")
    op.execute("""
        ALTER TABLE consumption_data
        ADD CONSTRAINT uq_consumption_data
        UNIQUE (usage_point_id, date, granularity, interval_start)
    """)

    op.execute("ALTER TABLE production_data DROP CONSTRAINT IF EXISTS uq_production_data")
    op.execute("""
        ALTER TABLE production_data
        ADD CONSTRAINT uq_production_data
        UNIQUE (usage_point_id, date, granularity, interval_start)
    """)
