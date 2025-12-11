"""add offer_url to energy_offers

Revision ID: 006
Revises: 005
Create Date: 2025-12-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add offer_url column to energy_offers table
    op.add_column('energy_offers', sa.Column('offer_url', sa.String(length=1024), nullable=True))


def downgrade() -> None:
    # Remove offer_url column from energy_offers table
    op.drop_column('energy_offers', 'offer_url')
