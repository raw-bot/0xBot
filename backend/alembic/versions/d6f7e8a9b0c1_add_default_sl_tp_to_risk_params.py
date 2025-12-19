"""add_sl_tp_to_risk_params

Revision ID: d6f7e8a9b0c1
Revises: c5d8e9f1a2b3
Create Date: 2025-10-26 16:17:00.000000

OPTIONAL MIGRATION: The code uses fallback values (0.035 and 0.07) if these params are missing.
This migration is only needed to explicitly set values in the database for clarity.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd6f7e8a9b0c1'
down_revision: Union[str, Sequence[str], None] = 'c5d8e9f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add stop_loss_pct and take_profit_pct to risk_params (optional)."""
    # Update all existing bots to include the new risk_params
    # This is optional since the code has fallback values
    op.execute("""
        UPDATE bots
        SET risk_params = risk_params ||
            '{"stop_loss_pct": 0.035, "take_profit_pct": 0.07}'::jsonb
        WHERE NOT (risk_params ? 'stop_loss_pct')
    """)


def downgrade() -> None:
    """Remove stop_loss_pct and take_profit_pct from risk_params."""
    op.execute("""
        UPDATE bots
        SET risk_params = risk_params - 'stop_loss_pct' - 'take_profit_pct'
    """)