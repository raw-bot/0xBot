#!/usr/bin/env python3
"""Run a dry-run trading cycle with mocked trade execution."""
import asyncio
import logging
from unittest.mock import MagicMock

from dotenv import load_dotenv
from sqlalchemy import select

from utils import DBSession, RED, GREEN, NC

from src.models.bot import Bot
from src.services.trading_engine_service import TradingEngine

load_dotenv()
logging.basicConfig(level=logging.INFO)


async def run_monk_cycle():
    print(f"{GREEN}Running Monk Mode Dry Run...{NC}")

    async with DBSession() as db:
        result = await db.execute(select(Bot).limit(1))
        bot = result.scalar_one_or_none()

        if not bot:
            print(f"{RED}No bot found. Create one first.{NC}")
            return

        print(f"Using Bot: {bot.name} (ID: {bot.id})")

        engine = TradingEngine(bot, db)

        # Mock trade executor to prevent real orders
        engine.trade_executor = MagicMock()
        engine.trade_executor.execute_entry = MagicMock(
            side_effect=lambda *args, **kwargs: print(f"[MOCK] Entry: {kwargs}")
        )
        engine.trade_executor.execute_exit = MagicMock(
            side_effect=lambda *args, **kwargs: print(f"[MOCK] Exit: {kwargs}")
        )

        print("\nStarting Trading Cycle...")
        await engine._trading_cycle()
        print(f"\n{GREEN}Cycle Complete.{NC}")


if __name__ == "__main__":
    asyncio.run(run_monk_cycle())
