"""Block: Execution - Handles trade execution.

This block is responsible for:
- Opening new positions
- Closing existing positions
- Recording trades to database
- Updating bot capital
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import config
from ..core.database import AsyncSessionLocal
from ..core.exchange_client import get_exchange_client
from ..core.logger import get_logger
from ..models.bot import Bot
from ..models.position import Position, PositionSide, PositionStatus
from ..models.trade import Trade, TradeSide

logger = get_logger(__name__)


@dataclass
class ExecutionResult:
    """Result of a trade execution."""

    success: bool
    position: Optional[Position] = None
    trade: Optional[Trade] = None
    error: Optional[str] = None


class ExecutionBlock:
    """Handles trade execution."""

    def __init__(self, bot_id: uuid.UUID):
        self.bot_id = bot_id
        self.exchange = get_exchange_client()

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
        """
        Open a new position.

        Returns:
            ExecutionResult with position and trade
        """
        async with AsyncSessionLocal() as db:
            try:
                # Get bot
                query = select(Bot).where(Bot.id == self.bot_id)
                result = await db.execute(query)
                bot = result.scalar_one()

                # Calculate position size
                margin = bot.capital * Decimal(str(size_pct))
                notional = margin * Decimal(str(leverage))
                quantity = notional / entry_price

                # Place order (paper trading mode)
                logger.info(f"PAPER: {side} {quantity:.6f} {symbol} @ {entry_price:,.2f}")

                # Create position
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

                # Create trade record
                fees = notional * Decimal("0.001")  # 0.1% fee
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

                # Deduct margin from capital
                bot.capital = bot.capital - margin - fees

                await db.commit()

                logger.info(
                    f"Position created: Entry @ {entry_price:,.2f}, "
                    f"SL @ {stop_loss:,.2f}, TP @ {take_profit:,.2f}"
                )
                logger.info(f"Entry executed: Capital: ${float(bot.capital):,.2f}")

                return ExecutionResult(
                    success=True,
                    position=position,
                    trade=trade,
                )

            except Exception as e:
                logger.error(f"Error opening position: {e}")
                return ExecutionResult(success=False, error=str(e))

    async def close_position(
        self,
        position: Position,
        current_price: Decimal,
        reason: str = "manual",
    ) -> ExecutionResult:
        """
        Close an existing position.

        Returns:
            ExecutionResult with trade
        """
        async with AsyncSessionLocal() as db:
            try:
                # Refresh position from DB
                query = select(Position).where(Position.id == position.id)
                result = await db.execute(query)
                position = result.scalar_one()

                if position.status != PositionStatus.OPEN:
                    return ExecutionResult(success=False, error="Position already closed")

                # Get bot
                bot_query = select(Bot).where(Bot.id == self.bot_id)
                bot_result = await db.execute(bot_query)
                bot = bot_result.scalar_one()

                # Calculate PnL
                if position.side == PositionSide.LONG:
                    pnl = (current_price - position.entry_price) * position.quantity
                else:
                    pnl = (position.entry_price - current_price) * position.quantity

                # Calculate margin to return
                margin = position.entry_price * position.quantity / position.leverage
                fees = current_price * position.quantity * Decimal("0.001")

                # Create exit trade
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

                # Update position
                position.status = PositionStatus.CLOSED
                position.current_price = current_price
                position.closed_at = datetime.utcnow()

                # Return margin + PnL to capital
                bot.capital = bot.capital + margin + pnl - fees

                await db.commit()

                pnl_str = f"+${float(pnl):,.2f}" if pnl >= 0 else f"-${abs(float(pnl)):,.2f}"
                logger.info(
                    f"✅ EXIT {position.symbol} @ ${current_price:,.2f} "
                    f"| PnL: {pnl_str} | Reason: {reason}"
                )

                return ExecutionResult(
                    success=True,
                    position=position,
                    trade=trade,
                )

            except Exception as e:
                logger.error(f"Error closing position: {e}")
                return ExecutionResult(success=False, error=str(e))
