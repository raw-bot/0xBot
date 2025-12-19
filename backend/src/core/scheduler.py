"""Background scheduler for managing trading engine instances."""

import asyncio
import uuid
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.logger import get_logger
from ..models.bot import Bot, BotStatus
from ..services.bot_service import BotService
from ..services.trading_engine_service import TradingEngine

logger = get_logger(__name__)


class BotScheduler:
    """
    Scheduler for managing multiple trading bot engines.
    
    Responsibilities:
    - Start trading engines for active bots
    - Stop trading engines for inactive bots
    - Monitor bot status changes
    - Handle engine lifecycle
    """
    
    def __init__(self):
        """Initialize the bot scheduler."""
        self.active_engines: Dict[uuid.UUID, TradingEngine] = {}
        self.engine_tasks: Dict[uuid.UUID, asyncio.Task] = {}
        self.is_running = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        logger.info("Bot scheduler initialized")
    
    async def start(self) -> None:
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return
        
        self.is_running = True
        logger.info("Starting bot scheduler")
        
        # Start monitoring task
        self.monitor_task = asyncio.create_task(self._monitor_bots())
    
    async def stop(self) -> None:
        """Stop the scheduler and all engines."""
        logger.info("Stopping bot scheduler")
        self.is_running = False
        
        # Cancel monitor task
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        # Stop all engines
        engine_ids = list(self.active_engines.keys())
        for bot_id in engine_ids:
            await self.stop_bot(bot_id)
        
        logger.info("Bot scheduler stopped")
    
    async def _monitor_bots(self) -> None:
        """Monitor bots and manage their engines."""
        logger.info("🔍 Bot monitor started (checks every 30s)")
        
        while self.is_running:
            try:
                async for db in get_db():
                    await self._check_and_update_engines(db)
                    break
                
                # Wait before next check
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Monitor error: {e}", exc_info=True)
                await asyncio.sleep(30)
    
    async def _check_and_update_engines(self, db: AsyncSession) -> None:
        """Check bot statuses and start/stop engines as needed."""
        try:
            bot_service = BotService(db)
            active_bots = await bot_service.get_active_bots()
            active_bot_ids = {bot.id for bot in active_bots}
            
            if not active_bots and not self.active_engines:
                logger.warning("⚠️  No active bots")
                return
            
            # Start engines for new active bots
            for bot in active_bots:
                if bot.id not in self.active_engines:
                    logger.info(f"🚀 Starting {bot.name}")
                    await self.start_bot(bot.id, db)
            
            # Stop engines for bots that are no longer active
            for bot_id in list(self.active_engines.keys()):
                if bot_id not in active_bot_ids:
                    logger.info(f"🛑 Stopping bot {bot_id}")
                    await self.stop_bot(bot_id)
            
        except Exception as e:
            logger.error(f"❌ Engine check error: {e}", exc_info=True)
    
    async def start_bot(self, bot_id: uuid.UUID, db: Optional[AsyncSession] = None) -> bool:
        """
        Start a trading engine for a bot.
        
        Args:
            bot_id: Bot UUID
            db: Optional database session (will create if not provided)
            
        Returns:
            True if started successfully, False otherwise
        """
        try:
            # Check if already running
            if bot_id in self.active_engines:
                logger.warning(f"Engine for bot {bot_id} is already running")
                return False
            
            # Get database session if not provided
            if db is None:
                async for session in get_db():
                    db = session
                    break
            
            # Get bot from database
            bot_service = BotService(db)
            bot = await bot_service.get_bot(bot_id)
            
            if not bot:
                logger.error(f"Bot {bot_id} not found")
                return False
            
            if bot.status != BotStatus.ACTIVE:
                logger.error(f"Bot {bot_id} is not active (status: {bot.status})")
                return False
            
            # Create trading engine
            engine = TradingEngine(
                bot=bot,
                db=db,
                cycle_interval=180  # 3 minutes
            )
            
            # Start engine in background task
            task = asyncio.create_task(engine.start())
            
            # Store engine and task
            self.active_engines[bot_id] = engine
            self.engine_tasks[bot_id] = task
            
            logger.info(f"✅ {bot.name} | {bot.model_name} | ${bot.capital:,.2f} | {engine.cycle_interval//60}min cycles")
            return True
            
        except Exception as e:
            logger.error(f"Error starting engine for bot {bot_id}: {e}", exc_info=True)
            return False
    
    async def stop_bot(self, bot_id: uuid.UUID) -> bool:
        """
        Stop a trading engine for a bot.
        
        Args:
            bot_id: Bot UUID
            
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            # Check if engine exists
            if bot_id not in self.active_engines:
                logger.warning(f"No engine running for bot {bot_id}")
                return False
            
            engine = self.active_engines[bot_id]
            task = self.engine_tasks.get(bot_id)
            
            # Stop the engine
            await engine.stop()
            
            # Cancel the task if still running
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Remove from tracking
            del self.active_engines[bot_id]
            if bot_id in self.engine_tasks:
                del self.engine_tasks[bot_id]
            
            logger.info(f"Trading engine stopped for bot {bot_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping engine for bot {bot_id}: {e}", exc_info=True)
            return False
    
    async def restart_bot(self, bot_id: uuid.UUID) -> bool:
        """
        Restart a trading engine for a bot.
        
        Args:
            bot_id: Bot UUID
            
        Returns:
            True if restarted successfully, False otherwise
        """
        await self.stop_bot(bot_id)
        await asyncio.sleep(1)  # Brief pause
        return await self.start_bot(bot_id)
    
    def get_active_engines(self) -> Dict[uuid.UUID, TradingEngine]:
        """
        Get all currently active engines.
        
        Returns:
            Dictionary of bot_id -> TradingEngine
        """
        return self.active_engines.copy()
    
    def get_engine_status(self, bot_id: uuid.UUID) -> Optional[dict]:
        """
        Get status information for a specific engine.
        
        Args:
            bot_id: Bot UUID
            
        Returns:
            Status dict or None if engine not found
        """
        if bot_id not in self.active_engines:
            return None
        
        engine = self.active_engines[bot_id]
        task = self.engine_tasks.get(bot_id)
        
        return {
            "bot_id": str(bot_id),
            "bot_name": engine.bot.name,
            "is_running": engine.is_running,
            "status": engine.bot.status,
            "task_done": task.done() if task else True,
            "cycle_interval": engine.cycle_interval
        }
    
    def get_all_status(self) -> list[dict]:
        """
        Get status for all active engines.
        
        Returns:
            List of status dicts
        """
        return [
            self.get_engine_status(bot_id)
            for bot_id in self.active_engines.keys()
        ]


# Global scheduler instance
_scheduler: Optional[BotScheduler] = None


def get_scheduler() -> BotScheduler:
    """
    Get or create the global scheduler instance.
    
    Returns:
        BotScheduler instance
    """
    global _scheduler
    
    if _scheduler is None:
        _scheduler = BotScheduler()
    
    return _scheduler


async def start_scheduler() -> None:
    """Start the global scheduler."""
    scheduler = get_scheduler()
    await scheduler.start()


async def stop_scheduler() -> None:
    """Stop the global scheduler."""
    scheduler = get_scheduler()
    await scheduler.stop()