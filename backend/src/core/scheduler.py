"""Background scheduler for managing trading engine instances."""

import asyncio
import uuid
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.llm_client import LLMClient, get_llm_client
from ..core.logger import get_logger
from ..core.memory.initialization import initialize_memory_system
from ..models.bot import BotStatus
from ..services.bot_service import BotService

USE_BLOCKS = True

if USE_BLOCKS:
    from ..blocks.orchestrator import TradingOrchestrator
else:
    from ..services.trading_engine_service import TradingEngine

logger = get_logger(__name__)


class BotScheduler:
    """Scheduler for managing multiple trading bot engines."""

    def __init__(self):
        """Initialize the bot scheduler."""
        self.active_engines: Dict[uuid.UUID, Any] = {}
        self.engine_tasks: Dict[uuid.UUID, asyncio.Task] = {}
        self.is_running = False
        self.monitor_task: Optional[asyncio.Task] = None
        logger.info("Bot scheduler initialized")

    async def start(self) -> None:
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        # Initialize memory system at scheduler startup
        try:
            initialize_memory_system()
            logger.info("✓ Memory system initialized")
        except Exception as e:
            logger.warning(f"Memory initialization warning: {e}")

        self.is_running = True
        logger.info("Starting bot scheduler")
        self.monitor_task = asyncio.create_task(self._monitor_bots())

    async def stop(self) -> None:
        """Stop the scheduler and all engines."""
        logger.info("Stopping bot scheduler")
        self.is_running = False

        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        for bot_id in list(self.active_engines.keys()):
            await self.stop_bot(bot_id)

        logger.info("Bot scheduler stopped")

    async def _monitor_bots(self) -> None:
        """Monitor bots and manage their engines."""
        logger.info("Bot monitor started (checks every 30s)")

        while self.is_running:
            try:
                async for db in get_db():
                    await self._check_and_update_engines(db)
                    break
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Monitor error: {e}", exc_info=True)
                await asyncio.sleep(30)

    async def _check_and_update_engines(self, db: AsyncSession) -> None:
        """Check bot statuses and start/stop engines as needed."""
        try:
            bot_service = BotService(db)
            active_bots = await bot_service.get_active_bots()
            active_bot_ids = {bot.id for bot in active_bots}

            if not active_bots and not self.active_engines:
                logger.warning("No active bots")
                return

            # Start engines for new active bots
            for bot in active_bots:
                if bot.id not in self.active_engines:
                    logger.info(f"Starting {bot.name}")
                    await self.start_bot(bot.id, db)

            # Stop engines for bots that are no longer active
            for bot_id in list(self.active_engines.keys()):
                if bot_id not in active_bot_ids:
                    logger.info(f"Stopping bot {bot_id}")
                    await self.stop_bot(bot_id)

        except Exception as e:
            logger.error(f"Engine check error: {e}", exc_info=True)

    async def start_bot(self, bot_id: uuid.UUID, db: Optional[AsyncSession] = None) -> bool:
        """Start a trading engine for a bot."""
        try:
            if bot_id in self.active_engines:
                logger.warning(f"Engine for bot {bot_id} is already running")
                return False

            if db is None:
                async for session in get_db():
                    db = session
                    break

            bot_service = BotService(db)
            bot = await bot_service.get_bot(bot_id)

            if not bot:
                logger.error(f"Bot {bot_id} not found")
                return False

            if bot.status != BotStatus.ACTIVE:
                logger.error(f"Bot {bot_id} is not active (status: {bot.status})")
                return False

            cycle_interval = 180  # 3 minutes
            if USE_BLOCKS:
                # Use Trinity indicator framework (confluence scoring)
                llm_client = get_llm_client()
                engine = TradingOrchestrator(
                    bot_id=bot.id,
                    cycle_interval=cycle_interval,
                    llm_client=llm_client,
                    decision_mode="trinity",  # ← Trinity indicator framework
                    paper_trading=bot.paper_trading  # ← Pass OKX live/paper trading setting
                )
                logger.info(f"[DECISION] Using Trinity indicator framework (confluence scoring)")
            else:
                engine = TradingEngine(bot=bot, db=db, cycle_interval=cycle_interval)

            task = asyncio.create_task(engine.start())
            self.active_engines[bot_id] = engine
            self.engine_tasks[bot_id] = task

            logger.info(
                f"{bot.name} | {bot.model_name} | ${bot.capital:,.2f} | {cycle_interval // 60}min cycles"
            )
            return True

        except Exception as e:
            logger.error(f"Error starting engine for bot {bot_id}: {e}", exc_info=True)
            return False

    async def stop_bot(self, bot_id: uuid.UUID) -> bool:
        """Stop a trading engine for a bot."""
        try:
            if bot_id not in self.active_engines:
                logger.warning(f"No engine running for bot {bot_id}")
                return False

            engine = self.active_engines[bot_id]
            task = self.engine_tasks.get(bot_id)

            await engine.stop()

            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            del self.active_engines[bot_id]
            self.engine_tasks.pop(bot_id, None)

            logger.info(f"Trading engine stopped for bot {bot_id}")
            return True

        except Exception as e:
            logger.error(f"Error stopping engine for bot {bot_id}: {e}", exc_info=True)
            return False

    async def restart_bot(self, bot_id: uuid.UUID) -> bool:
        """Restart a trading engine for a bot."""
        await self.stop_bot(bot_id)
        await asyncio.sleep(1)
        return await self.start_bot(bot_id)

    def get_active_engines(self) -> Dict[uuid.UUID, Any]:
        """Get all currently active engines."""
        return self.active_engines.copy()

    def get_engine_status(self, bot_id: uuid.UUID) -> Optional[dict]:
        """Get status information for a specific engine."""
        if bot_id not in self.active_engines:
            return None

        engine = self.active_engines[bot_id]
        task = self.engine_tasks.get(bot_id)

        return {
            "bot_id": str(bot_id),
            "is_running": getattr(engine, "is_running", getattr(engine, "_running", False)),
            "task_done": task.done() if task else True,
            "cycle_interval": engine.cycle_interval,
        }

    def get_all_status(self) -> list[dict]:
        """Get status for all active engines."""
        return [self.get_engine_status(bot_id) for bot_id in self.active_engines.keys()]


_scheduler: Optional[BotScheduler] = None


def get_scheduler() -> BotScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BotScheduler()
    return _scheduler


async def start_scheduler() -> None:
    """Start the global scheduler."""
    await get_scheduler().start()


async def stop_scheduler() -> None:
    """Stop the global scheduler."""
    await get_scheduler().stop()
