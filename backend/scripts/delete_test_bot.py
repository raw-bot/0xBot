#!/usr/bin/env python3
"""Delete a bot by ID."""
import asyncio
import sys
import uuid

from sqlalchemy import select

from utils import DBSession, GREEN, YELLOW, RED, NC

from src.models.bot import Bot


async def delete_bot(bot_id: str):
    try:
        bot_uuid = uuid.UUID(bot_id)
    except ValueError:
        print(f"{RED}Invalid UUID: {bot_id}{NC}")
        return

    async with DBSession() as db:
        result = await db.execute(select(Bot).where(Bot.id == bot_uuid))
        bot = result.scalar_one_or_none()

        if not bot:
            print(f"{YELLOW}Bot not found: {bot_id}{NC}")
            return

        await db.delete(bot)
        await db.commit()
        print(f"{GREEN}Bot deleted: {bot_id}{NC}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python delete_test_bot.py <bot_id>")
        sys.exit(1)
    asyncio.run(delete_bot(sys.argv[1]))
