import asyncio
import logging

from sqlalchemy import text
from src.core.database import engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def patch_database():
    """Add leverage column to positions table if it doesn't exist."""
    logger.info("Starting database patch...")

    async with engine.begin() as conn:
        try:
            # Check if column exists
            logger.info("Checking if 'leverage' column exists in 'positions' table...")
            result = await conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='positions' AND column_name='leverage'"
                )
            )
            column_exists = result.scalar() is not None

            if column_exists:
                logger.info("Column 'leverage' already exists. Skipping.")
            else:
                logger.info("Adding 'leverage' column to 'positions' table...")
                await conn.execute(
                    text(
                        "ALTER TABLE positions ADD COLUMN leverage NUMERIC(10, 2) DEFAULT 10.0 NOT NULL"
                    )
                )
                logger.info("Column added successfully.")

        except Exception as e:
            logger.error(f"Error patching database: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(patch_database())
