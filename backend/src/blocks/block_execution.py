"""Block: Execution - Handles trade execution."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select

from ..core.config import config
from ..core.database import AsyncSessionLocal
from ..core.exchange_client import get_exchange_client
from ..core.logger import get_logger
from ..core.memory.memory_manager import MemoryManager
from ..models.bot import Bot
from ..models.position import Position, PositionSide, PositionStatus
from ..models.trade import Trade, TradeSide
from ..services.trading_memory_service import TradingMemoryService

logger = get_logger(__name__)

FEE_RATE = Decimal("0.001")


@dataclass
class ExecutionResult:
    """Result of a trade execution."""

    success: bool
    position: Optional[Position] = None
    trade: Optional[Trade] = None
    error: Optional[str] = None


class ExecutionBlock:
    """Handles trade execution with memory integration for learning."""

    def __init__(self, bot_id: uuid.UUID, paper_trading: bool = True):
        self.bot_id = bot_id
        self.exchange = get_exchange_client(paper_trading=paper_trading)
        self.memory = TradingMemoryService(bot_id)

    async def open_position(
        self,
        symbol: str,
        side: str,
        size_pct: float,
        entry_price: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal,
        leverage: int = int(config.DEFAULT_LEVERAGE),
    ) -> ExecutionResult:
        """Open a new position."""
        async with AsyncSessionLocal() as db:
            try:
                bot = await self._get_bot(db)

                margin = bot.capital * Decimal(str(size_pct))
                notional = margin * Decimal(str(leverage))
                quantity = notional / entry_price
                fees = notional * FEE_RATE

                logger.info(f"PAPER: {side} {quantity:.6f} {symbol} @ {entry_price:,.2f}")

                position = Position(
                    bot_id=self.bot_id,
                    symbol=symbol,
                    side=PositionSide.LONG if side == "long" else PositionSide.SHORT,
                    quantity=quantity,
                    entry_price=entry_price,
                    current_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    leverage=Decimal(str(leverage)),
                    status=PositionStatus.OPEN,
                    opened_at=datetime.utcnow(),
                )
                db.add(position)
                await db.flush()

                trade = Trade(
                    bot_id=self.bot_id,
                    position_id=position.id,
                    symbol=symbol,
                    side=TradeSide.BUY if side == "long" else TradeSide.SELL,
                    quantity=quantity,
                    price=entry_price,
                    fees=fees,
                    realized_pnl=Decimal("0"),
                    executed_at=datetime.utcnow(),
                )
                db.add(trade)

                bot.capital = bot.capital - margin - fees
                await db.commit()

                logger.info(f"Entry executed: Capital: ${float(bot.capital):,.2f}")

                return ExecutionResult(success=True, position=position, trade=trade)

            except Exception as e:
                logger.error(f"Error opening position: {e}")
                return ExecutionResult(success=False, error=str(e))

    async def close_position(
        self,
        position: Position,
        current_price: Decimal,
        reason: str = "manual",
    ) -> ExecutionResult:
        """Close an existing position."""
        async with AsyncSessionLocal() as db:
            try:
                position = await self._refresh_position(db, position.id)
                if position.status != PositionStatus.OPEN:
                    return ExecutionResult(success=False, error="Position already closed")

                bot = await self._get_bot(db)

                pnl = self._calculate_pnl(position, current_price)
                margin = position.entry_price * position.quantity / position.leverage
                fees = current_price * position.quantity * FEE_RATE

                trade = Trade(
                    bot_id=self.bot_id,
                    position_id=position.id,
                    symbol=position.symbol,
                    side=TradeSide.SELL if position.side == PositionSide.LONG else TradeSide.BUY,
                    quantity=position.quantity,
                    price=current_price,
                    fees=fees,
                    realized_pnl=pnl,
                    executed_at=datetime.utcnow(),
                )
                db.add(trade)

                position.status = PositionStatus.CLOSED
                position.current_price = current_price
                position.closed_at = datetime.utcnow()

                bot.capital = bot.capital + margin + pnl - fees
                await db.commit()

                pnl_str = f"+${float(pnl):,.2f}" if pnl >= 0 else f"-${abs(float(pnl)):,.2f}"
                logger.info(f"EXIT {position.symbol} @ ${current_price:,.2f} | PnL: {pnl_str} | Reason: {reason}")

                # Record outcome in memory for learning
                if MemoryManager.is_enabled():
                    await self._record_trade_outcome(position, pnl, reason)

                return ExecutionResult(success=True, position=position, trade=trade)

            except Exception as e:
                logger.error(f"Error closing position: {e}")
                return ExecutionResult(success=False, error=str(e))

    async def _get_bot(self, db: Any) -> Bot:
        """Get bot from database."""
        result = await db.execute(select(Bot).where(Bot.id == self.bot_id))
        bot = result.scalar_one_or_none()
        if not bot:
            raise ValueError(f"Bot {self.bot_id} not found in database")
        return bot  # type: ignore[no-any-return]

    async def _refresh_position(self, db: Any, position_id: uuid.UUID) -> Position:
        """Refresh position from database."""
        result = await db.execute(select(Position).where(Position.id == position_id))
        position = result.scalar_one_or_none()
        if not position:
            raise ValueError(f"Position {position_id} not found in database")
        return position  # type: ignore[no-any-return]

    def _calculate_pnl(self, position: Position, current_price: Decimal) -> Decimal:
        """Calculate PnL for a position."""
        if position.side == PositionSide.LONG:
            return (current_price - position.entry_price) * position.quantity
        return (position.entry_price - current_price) * position.quantity

    async def _record_trade_outcome(
        self, position: Position, pnl: Decimal, reason: str
    ) -> None:
        """Record trade outcome in memory for future learning.

        Args:
            position: Closed position
            pnl: Realized PnL
            reason: Why the position was closed
        """
        try:
            # Create a pattern entry for memory
            entry_pattern = {
                "side": str(position.side.value) if hasattr(position.side, 'value') else str(position.side),
                "entry_price": float(position.entry_price),
                "exit_price": float(position.current_price),
                "stop_loss": float(position.stop_loss) if position.stop_loss else None,
                "take_profit": float(position.take_profit) if position.take_profit else None,
                "close_reason": reason,
                "hold_hours": (position.closed_at - position.opened_at).total_seconds() / 3600
                if position.closed_at
                else 0,
            }

            # Record as profitable or losing setup
            if pnl > 0:
                await self.memory.remember_profitable_setup(
                    symbol=position.symbol,
                    entry_pattern=entry_pattern,
                    pnl=pnl,
                    confidence=Decimal("0.50"),  # Default confidence for recorded trade
                )
            else:
                await self.memory.remember_losing_setup(
                    symbol=position.symbol,
                    entry_pattern=entry_pattern,
                    pnl=pnl,
                )

            # Update symbol stats
            # (This would normally be done by StrategyPerformanceService)
            logger.debug(f"[MEMORY] Recorded outcome for {position.symbol}: PnL=${float(pnl):.2f}")

        except Exception as e:
            logger.warning(f"[MEMORY] Failed to record outcome for {position.symbol}: {e}")
