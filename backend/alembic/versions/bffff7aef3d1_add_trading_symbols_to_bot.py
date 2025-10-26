"""add_trading_symbols_to_bot

Revision ID: bffff7aef3d1
Revises: c5d8e9f1a2b3
Create Date: 2025-10-25 18:53:48.065938

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bffff7aef3d1'
down_revision: Union[str, Sequence[str], None] = 'c5d8e9f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add trading_symbols column to bots table."""
    # Add trading_symbols column as JSON with default value ["BTC/USDT"]
    op.add_column('bots', sa.Column('trading_symbols', sa.JSON(), nullable=False, server_default='["BTC/USDT"]'))


def downgrade() -> None:
    """Downgrade schema - Remove trading_symbols column from bots table."""
    op.drop_column('bots', 'trading_symbols')
