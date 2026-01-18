#!/usr/bin/env python3
"""Add leverage column to positions table if missing."""
import asyncio
import logging

from sqlalchemy import text
from src.core.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def patch_database():
    logger.info("Checking database schema...")

    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='positions' AND column_name='leverage'"
            )
        )

        if result.scalar() is not None:
            logger.info("Column 'leverage' already exists")
            return

        logger.info("Adding 'leverage' column...")
        await conn.execute(
            text(
                "ALTER TABLE positions ADD COLUMN leverage "
                "NUMERIC(10, 2) DEFAULT 10.0 NOT NULL"
            )
        )
        logger.info("Column added successfully")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(patch_database())
