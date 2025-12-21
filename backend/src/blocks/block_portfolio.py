"""Block: Portfolio - Manages portfolio state and equity tracking.

This block is responsible for:
- Getting current portfolio state (cash, positions, equity)
- Calculating unrealized PnL
- Recording equity snapshots for dashboard
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import AsyncSessionLocal
from ..core.logger import get_logger
from ..models.bot import Bot
from ..models.equity_snapshot import EquitySnapshot
from ..models.position import Position, PositionStatus

logger = get_logger(__name__)


@dataclass
class PortfolioState:
    """Current portfolio state."""

    cash: Decimal
    equity: Decimal
    initial_capital: Decimal
    unrealized_pnl: Decimal
    invested: Decimal
    return_pct: float
    open_positions: List[Position]


class PortfolioBlock:
    """Manages portfolio state and equity tracking."""

    def __init__(self, bot_id: uuid.UUID):
        self.bot_id = bot_id

    async def get_state(self, db: Optional[AsyncSession] = None) -> PortfolioState:
        """
        Get current portfolio state.

        Returns:
            PortfolioState with cash, equity, positions
        """
        close_session = False
        if db is None:
            db = AsyncSessionLocal()
            close_session = True

        try:
            # Get bot
            query = select(Bot).where(Bot.id == self.bot_id)
            result = await db.execute(query)
            bot = result.scalar_one()

            # Get open positions
            pos_query = select(Position).where(
                Position.bot_id == self.bot_id, Position.status == PositionStatus.OPEN
            )
            pos_result = await db.execute(pos_query)
            positions = list(pos_result.scalars().all())

            # Calculate values
            cash = Decimal(str(bot.capital))
            initial = Decimal(str(bot.initial_capital))

            # Margin locked in positions
            invested = sum(
                (
                    (p.entry_price * p.quantity / p.leverage)
                    if p.leverage
                    else (p.entry_price * p.quantity)
                )
                for p in positions
            )

            # Unrealized PnL
            unrealized_pnl = sum(p.unrealized_pnl for p in positions)

            # Total equity
            equity = cash + invested + unrealized_pnl

            # Return percentage
            return_pct = float((equity - initial) / initial * 100) if initial > 0 else 0

            return PortfolioState(
                cash=cash,
                equity=equity,
                initial_capital=initial,
                unrealized_pnl=unrealized_pnl,
                invested=invested,
                return_pct=return_pct,
                open_positions=positions,
            )

        finally:
            if close_session:
                await db.close()

    async def record_snapshot(self) -> None:
        """Record equity snapshot for dashboard chart."""
        try:
            async with AsyncSessionLocal() as db:
                state = await self.get_state(db)

                snapshot = EquitySnapshot(
                    bot_id=self.bot_id,
                    equity=state.equity,
                    cash=state.cash,
                    unrealized_pnl=state.unrealized_pnl,
                )
                db.add(snapshot)
                await db.commit()

                logger.info(
                    f"📊 Equity: ${float(state.equity):,.2f} "
                    f"(cash: ${float(state.cash):,.2f}, "
                    f"unrealized: ${float(state.unrealized_pnl):,.2f})"
                )

        except Exception as e:
            logger.error(f"Error recording equity snapshot: {e}")

    async def get_positions_by_symbol(self, symbol: str) -> List[Position]:
        """Get open positions for a specific symbol."""
        async with AsyncSessionLocal() as db:
            query = select(Position).where(
                Position.bot_id == self.bot_id,
                Position.symbol == symbol,
                Position.status == PositionStatus.OPEN,
            )
            result = await db.execute(query)
            return list(result.scalars().all())
