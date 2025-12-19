import asyncio
import logging
import os
import sys
from unittest.mock import MagicMock

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from dotenv import load_dotenv
from sqlalchemy import select
from src.core.database import get_db
from src.models.bot import Bot
from src.services.trading_engine_service import TradingEngine

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_monk_cycle():
    print("🧘 Running Monk Mode Dry Run...")

    # 1. Get a Bot (or mock one)
    # We need a real bot ID to fetch positions, but we can mock the rest
    async for db in get_db():
        result = await db.execute(select(Bot).limit(1))
        bot = result.scalar_one_or_none()
        if not bot:
            print("❌ No bot found in DB. Please create one first.")
            return

        print(f"🤖 Using Bot: {bot.name} (ID: {bot.id})")

        # 2. Initialize Trading Engine
        engine = TradingEngine(bot, db)

        # 3. Mock Trade Executor to prevent real orders
        engine.trade_executor = MagicMock()
        engine.trade_executor.execute_entry = MagicMock(
            side_effect=lambda *args, **kwargs: print(f"🚫 [MOCK] Execute Entry: {kwargs}")
        )
        engine.trade_executor.execute_exit = MagicMock(
            side_effect=lambda *args, **kwargs: print(f"🚫 [MOCK] Execute Exit: {kwargs}")
        )

        # 4. Run Cycle
        print("\n🚀 Starting Trading Cycle...")
        await engine._trading_cycle()

        print("\n✅ Cycle Complete.")
        break


if __name__ == "__main__":
    asyncio.run(run_monk_cycle())
