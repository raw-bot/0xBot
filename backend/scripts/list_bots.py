import asyncio
import sys
from pathlib import Path

from sqlalchemy import select
from src.core.database import AsyncSessionLocal
from src.models.bot import Bot

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def list_bots():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Bot))
        bots = result.scalars().all()

        print(f"Found {len(bots)} bots:")
        for bot in bots:
            print(f"- ID: {bot.id}")
            print(f"  Name: {bot.name}")
            print(f"  Status: {bot.status}")
            print(f"  Capital: ${bot.capital:,.2f}")
            print("-" * 20)


if __name__ == "__main__":
    asyncio.run(list_bots())
