"""Trading engine service - facade for backward compatibility."""

import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import AsyncSessionLocal
from ...core.llm_client import LLMClient
from ...core.logger import get_logger
from ...models.bot import Bot, BotStatus
from sqlalchemy import select
from .cycle_manager import TradingCycleManager
from .decision_executor import DecisionExecutor
from .position_monitor import PositionMonitor
from ...core.service_factories import create_trading_cycle_manager

logger = get_logger(__name__)


class TradingEngineService:
    """Trading engine service - main facade maintaining backward compatibility."""

    def __init__(
        self,
        bot: Bot,
        db: AsyncSession,
        cycle_interval: int = 300,
        llm_client: Optional[LLMClient] = None,
    ):
        self.bot_id = bot.id
        self.bot = bot
        self.db = db
        self.cycle_interval = cycle_interval
        self.is_running = False
        self.cycle_count = 0
        self.session_start = datetime.utcnow()

        self.cycle_manager = create_trading_cycle_manager(bot, db, llm_client)
        self.decision_executor = DecisionExecutor(db, bot.id)
        self.position_monitor = PositionMonitor(db, bot.id)

        logger.info(f"Trading engine service initialized for bot {bot.id} ({bot.name})")

    async def start(self) -> None:
        """Start the trading engine loop."""
        if self.is_running:
            logger.warning(f"Engine already running for bot {self.bot_id}")
            return

        self.is_running = True
        logger.info(f"Starting trading engine for bot {self.bot_id}")

        try:
            bot_status = await self._get_bot_status()
            while self.is_running and bot_status == BotStatus.ACTIVE:
                try:
                    # Execute trading cycle
                    decisions, all_coins_data, all_positions = await self.cycle_manager.execute_cycle()

                    # Execute decisions if cycle completed successfully
                    if decisions and all_coins_data and all_positions is not None:
                        bot_obj = await self._get_fresh_bot()
                        await self.decision_executor.execute_decisions(
                            all_coins_data, decisions, all_positions, bot_obj
                        )

                    # Monitor positions between cycles
                    all_positions = await self.cycle_manager.position_service.get_open_positions(
                        self.bot_id
                    )
                    await self.position_monitor.monitor_positions(all_positions)

                    self.cycle_count += 1
                except Exception as e:
                    logger.error(f"Error in trading cycle: {e}")

                await asyncio.sleep(self.cycle_interval)
                bot_status = await self._get_bot_status()
        finally:
            self.is_running = False
            logger.info(f"Trading engine stopped for bot {self.bot_id}")

    async def stop(self) -> None:
        """Stop the trading engine and close all positions."""
        logger.info(f"Stopping trading engine for bot {self.bot_id}")
        self.is_running = False

        positions = await self.cycle_manager.position_service.get_open_positions(self.bot_id)
        for position in positions:
            try:
                ticker = await self.cycle_manager.market_data_service.fetch_ticker(position.symbol)
                await self.cycle_manager.trade_executor.execute_exit(
                    position=position, current_price=ticker.last, reason="engine_stopped"
                )
                logger.info(f"Closed position {position.id} on engine stop")
            except Exception as e:
                logger.error(f"Error closing position {position.id}: {e}")

        await self._update_bot_status(BotStatus.STOPPED)

    async def _get_bot_status(self) -> BotStatus:
        """Get the current bot status from database."""
        bot = await self._get_fresh_bot()
        return bot.status

    async def _get_fresh_bot(self) -> Bot:
        """Get fresh bot instance from database."""
        async with AsyncSessionLocal() as fresh_db:
            query = select(Bot).where(Bot.id == self.bot_id)
            result = await fresh_db.execute(query)
            return result.scalar_one()

    async def _update_bot_status(self, status: BotStatus) -> None:
        """Update bot status in database."""
        async with AsyncSessionLocal() as fresh_db:
            query = select(Bot).where(Bot.id == self.bot_id)
            result = await fresh_db.execute(query)
            bot = result.scalar_one()
            bot.status = status
            await fresh_db.commit()
