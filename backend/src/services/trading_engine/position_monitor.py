"""Position monitor - tracks and manages open positions."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.logger import get_logger
from ...models.position import Position, PositionStatus
from ..market_data_service import MarketDataService
from ..position_service import PositionService
from ..trade_executor_service import TradeExecutorService

logger = get_logger(__name__)


class PositionMonitor:
    """Monitors open positions and handles stop loss/take profit."""

    def __init__(self, db: AsyncSession, bot_id: UUID):
        self.db = db
        self.bot_id = bot_id
        self.market_data_service = MarketDataService()
        self.position_service = PositionService(db)
        self.trade_executor = TradeExecutorService(db)

    async def monitor_positions(self, positions: List[Position]) -> None:
        """Check if any positions should be closed due to stop loss or take profit."""
        if not positions:
            return

        logger.info(f"Checking exit conditions for {len(positions)} position(s)")

        for position in positions:
            if position.status != PositionStatus.OPEN:
                continue

            try:
                ticker = await self.market_data_service.fetch_ticker(position.symbol)
                current_price = ticker.last
                hold_hours = (datetime.utcnow() - position.opened_at).total_seconds() / 3600

                logger.info(
                    f"[{position.symbol}] Hold: {hold_hours:.1f}h | PnL: {position.unrealized_pnl_pct:+.2f}%"
                )

                if position.stop_loss is not None and position.take_profit is not None:
                    exit_reason = await self.position_service.check_stop_loss_take_profit(
                        position, Decimal(str(current_price))
                    )
                else:
                    exit_reason = None

                if exit_reason:
                    logger.info(f"{position.symbol} closing: {exit_reason.upper()}")
                    await self.trade_executor.execute_exit(
                        position=position, current_price=Decimal(str(current_price)), reason=exit_reason
                    )
            except Exception as e:
                logger.error(f"Error checking {position.symbol}: {e}")

    async def close_all_positions(self, positions: List[Position], current_price: Decimal) -> None:
        """Handle emergency close of all positions."""
        logger.warning("Processing emergency close...")
        for position in positions:
            await self.trade_executor.execute_exit(
                position=position, current_price=current_price, reason="emergency_close"
            )
            logger.info(f"EMERGENCY CLOSE {position.symbol.split('/')[0]} @ ${current_price:,.2f}")

    async def update_position_status(self, position_id: UUID, status: PositionStatus) -> None:
        """Update position status in database."""
        try:
            position = await self.position_service.get_position(position_id)
            if position:
                position.status = status
                await self.db.commit()
                logger.info(f"Position {position_id} status updated to {status}")
        except Exception as e:
            logger.error(f"Error updating position status: {e}")
