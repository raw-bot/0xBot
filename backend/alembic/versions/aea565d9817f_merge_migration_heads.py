"""Merge migration heads

Revision ID: aea565d9817f
Revises: bffff7aef3d1, d6f7e8a9b0c1
Create Date: 2026-01-10 11:00:13.188062

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aea565d9817f'
down_revision: Union[str, Sequence[str], None] = ('bffff7aef3d1', 'd6f7e8a9b0c1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
