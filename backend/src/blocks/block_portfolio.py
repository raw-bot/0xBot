"""Block: Portfolio - Manages portfolio state and equity tracking."""

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
        """Get current portfolio state."""
        should_close = db is None
        if should_close:
            db = AsyncSessionLocal()

        try:
            bot = await self._get_bot(db)  # type: ignore[arg-type]
            positions = await self._get_open_positions(db)  # type: ignore[arg-type]

            cash = Decimal(str(bot.capital))
            initial = Decimal(str(bot.initial_capital))

            invested = sum((self._calculate_margin(p) for p in positions), Decimal(0))
            unrealized_pnl = sum((p.unrealized_pnl for p in positions), Decimal(0))
            equity = cash + invested + unrealized_pnl
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
            if should_close and db is not None:
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
                    f"Equity: ${float(state.equity):,.2f} "
                    f"(cash: ${float(state.cash):,.2f}, unrealized: ${float(state.unrealized_pnl):,.2f})"
                )
        except Exception as e:
            logger.error(f"Error recording equity snapshot: {e}")

    async def get_positions_by_symbol(self, symbol: str) -> List[Position]:
        """Get open positions for a specific symbol."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Position).where(
                    Position.bot_id == self.bot_id,
                    Position.symbol == symbol,
                    Position.status == PositionStatus.OPEN,
                )
            )
            return list(result.scalars().all())

    async def _get_bot(self, db: AsyncSession) -> Bot:
        """Get bot from database."""
        result = await db.execute(select(Bot).where(Bot.id == self.bot_id))
        return result.scalar_one()

    async def _get_open_positions(self, db: AsyncSession) -> List[Position]:
        """Get all open positions for this bot."""
        result = await db.execute(
            select(Position).where(
                Position.bot_id == self.bot_id,
                Position.status == PositionStatus.OPEN,
            )
        )
        return list(result.scalars().all())

    def _calculate_margin(self, position: Position) -> Decimal:
        """Calculate margin locked in a position."""
        if position.leverage:
            return position.entry_price * position.quantity / position.leverage
        return position.entry_price * position.quantity
