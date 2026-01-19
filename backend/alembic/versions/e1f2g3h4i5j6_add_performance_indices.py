"""Add performance indices for common queries

Revision ID: e1f2g3h4i5j6
Revises: aea565d9817f
Create Date: 2026-01-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2g3h4i5j6'
down_revision: Union[str, Sequence[str], None] = 'aea565d9817f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add performance indices."""
    # Trade table indices
    # Index for dashboard historical trades (bot_id, created_at DESC)
    op.create_index(
        'idx_trade_bot_id_executed_at_desc',
        'trades',
        ['bot_id', sa.text('executed_at DESC')],
        unique=False
    )

    # Index for symbol analysis (symbol, created_at DESC)
    op.create_index(
        'idx_trade_symbol_executed_at_desc',
        'trades',
        ['symbol', sa.text('executed_at DESC')],
        unique=False
    )

    # Position table indices
    # Index for open positions per bot (bot_id, status)
    op.create_index(
        'idx_position_bot_id_status',
        'positions',
        ['bot_id', 'status'],
        unique=False
    )

    # Index for checking if symbol already has open position (bot_id, symbol, status)
    op.create_index(
        'idx_position_bot_id_symbol_status',
        'positions',
        ['bot_id', 'symbol', 'status'],
        unique=False
    )

    # Bot table index
    # Index for user bot filtering (user_id, bot_id)
    op.create_index(
        'idx_bot_user_id_bot_id',
        'bots',
        ['user_id', 'id'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema - Remove performance indices."""
    op.drop_index('idx_bot_user_id_bot_id', table_name='bots')
    op.drop_index('idx_position_bot_id_symbol_status', table_name='positions')
    op.drop_index('idx_position_bot_id_status', table_name='positions')
    op.drop_index('idx_trade_symbol_executed_at_desc', table_name='trades')
    op.drop_index('idx_trade_bot_id_executed_at_desc', table_name='trades')
