#!/usr/bin/env python3
"""List all bots in the database."""
import asyncio

from sqlalchemy import select

from utils import DBSession, print_bot_info

from src.models.bot import Bot


async def list_bots():
    async with DBSession() as db:
        result = await db.execute(select(Bot))
        bots = result.scalars().all()

        print(f"Found {len(bots)} bots:\n")
        for bot in bots:
            print_bot_info(bot)
            print("-" * 30)


if __name__ == "__main__":
    asyncio.run(list_bots())
