"""add_initial_capital_to_bot

Revision ID: c5d8e9f1a2b3
Revises: 558c0c1b4d5a
Create Date: 2025-10-25 14:19:30.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c5d8e9f1a2b3'
down_revision: Union[str, Sequence[str], None] = '558c0c1b4d5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add initial_capital column and initialize it with current capital value."""
    # Add the new column as nullable first
    op.add_column('bots', sa.Column('initial_capital', sa.Numeric(precision=20, scale=2), nullable=True))
    
    # Copy current capital values to initial_capital
    op.execute('UPDATE bots SET initial_capital = capital')
    
    # Now make it NOT NULL
    op.alter_column('bots', 'initial_capital', nullable=False)


def downgrade() -> None:
    """Remove initial_capital column."""
    op.drop_column('bots', 'initial_capital')