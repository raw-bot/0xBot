#!/usr/bin/env python3
"""Inspect a bot's details including risk parameters."""
import asyncio
import sys
import uuid

from sqlalchemy import select

from utils import DBSession, print_bot_info, YELLOW, NC

from src.models.bot import Bot


async def inspect_bot(bot_id: str):
    try:
        bot_uuid = uuid.UUID(bot_id)
    except ValueError:
        print(f"{YELLOW}Invalid UUID: {bot_id}{NC}")
        return

    async with DBSession() as db:
        result = await db.execute(select(Bot).where(Bot.id == bot_uuid))
        bot = result.scalar_one_or_none()

        if bot:
            print_bot_info(bot, detailed=True)
        else:
            print(f"{YELLOW}Bot not found{NC}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_bot.py <bot_id>")
        sys.exit(1)
    asyncio.run(inspect_bot(sys.argv[1]))
