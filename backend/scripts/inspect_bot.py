import asyncio
import sys
import uuid
from pathlib import Path

from sqlalchemy import select
from src.core.database import AsyncSessionLocal
from src.models.bot import Bot

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def inspect_bot_risk():
    bot_id = uuid.UUID("88e3df10-eb6e-4f13-8f3a-de24788944dd")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Bot).where(Bot.id == bot_id))
        bot = result.scalar_one_or_none()

        if bot:
            print(f"Bot: {bot.name}")
            print(f"Risk Params: {bot.risk_params}")
        else:
            print("Bot not found")


if __name__ == "__main__":
    asyncio.run(inspect_bot_risk())
