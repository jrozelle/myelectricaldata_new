"""Add ConsumptionFrance and GenerationForecast tables

Revision ID: 048bdc8487a5
Revises: 5f1308fff153
Create Date: 2026-01-11 23:30:43.461243

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "048bdc8487a5"
down_revision: Union[str, None] = "5f1308fff153"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Vérifie si une table existe déjà dans la base de données."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def index_exists(index_name: str, table_name: str) -> bool:
    """Vérifie si un index existe déjà sur une table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(idx["name"] == index_name for idx in indexes)


def upgrade() -> None:
    # Create consumption_france table (si elle n'existe pas)
    if not table_exists("consumption_france"):
        op.create_table(
            "consumption_france",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("type", sa.String(length=20), nullable=False),
            sa.Column("start_date", sa.DateTime(), nullable=False),
            sa.Column("end_date", sa.DateTime(), nullable=False),
            sa.Column("value", sa.Float(), nullable=False),
            sa.Column("updated_date", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    # Créer les index pour consumption_france (si ils n'existent pas)
    if table_exists("consumption_france"):
        if not index_exists("idx_consumption_france_start", "consumption_france"):
            op.create_index("idx_consumption_france_start", "consumption_france", ["start_date"], unique=False)
        if not index_exists("idx_consumption_france_type_start", "consumption_france"):
            op.create_index("idx_consumption_france_type_start", "consumption_france", ["type", "start_date"], unique=False)
        if not index_exists("ix_consumption_france_id", "consumption_france"):
            op.create_index(op.f("ix_consumption_france_id"), "consumption_france", ["id"], unique=False)

    # Create generation_forecast table (si elle n'existe pas)
    if not table_exists("generation_forecast"):
        op.create_table(
            "generation_forecast",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("production_type", sa.String(length=50), nullable=False),
            sa.Column("forecast_type", sa.String(length=20), nullable=False),
            sa.Column("start_date", sa.DateTime(), nullable=False),
            sa.Column("end_date", sa.DateTime(), nullable=False),
            sa.Column("value", sa.Float(), nullable=False),
            sa.Column("updated_date", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    # Créer les index pour generation_forecast (si ils n'existent pas)
    if table_exists("generation_forecast"):
        if not index_exists("idx_generation_forecast_prod_type", "generation_forecast"):
            op.create_index(
                "idx_generation_forecast_prod_type",
                "generation_forecast",
                ["production_type", "forecast_type", "start_date"],
                unique=False,
            )
        if not index_exists("idx_generation_forecast_start", "generation_forecast"):
            op.create_index("idx_generation_forecast_start", "generation_forecast", ["start_date"], unique=False)
        if not index_exists("ix_generation_forecast_id", "generation_forecast"):
            op.create_index(op.f("ix_generation_forecast_id"), "generation_forecast", ["id"], unique=False)


def downgrade() -> None:
    # Drop generation_forecast table
    op.drop_index(op.f("ix_generation_forecast_id"), table_name="generation_forecast")
    op.drop_index("idx_generation_forecast_start", table_name="generation_forecast")
    op.drop_index("idx_generation_forecast_prod_type", table_name="generation_forecast")
    op.drop_table("generation_forecast")

    # Drop consumption_france table
    op.drop_index(op.f("ix_consumption_france_id"), table_name="consumption_france")
    op.drop_index("idx_consumption_france_type_start", table_name="consumption_france")
    op.drop_index("idx_consumption_france_start", table_name="consumption_france")
    op.drop_table("consumption_france")
