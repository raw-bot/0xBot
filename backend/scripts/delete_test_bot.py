import asyncio
import sys
import uuid
from pathlib import Path

from sqlalchemy import delete, select
from src.core.database import AsyncSessionLocal
from src.models.bot import Bot

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def delete_test_bot():
    bot_id = uuid.UUID("c005bfa7-2bd8-4bcb-9fda-e88f5bddcae4")

    async with AsyncSessionLocal() as db:
        print(f"Deleting bot {bot_id}...")

        # Check if exists
        result = await db.execute(select(Bot).where(Bot.id == bot_id))
        bot = result.scalar_one_or_none()

        if bot:
            await db.delete(bot)
            await db.commit()
            print("✅ Bot deleted successfully")
        else:
            print("⚠️  Bot not found")


if __name__ == "__main__":
    asyncio.run(delete_test_bot())
