#!/usr/bin/env python3
"""Create a new test bot with $10,000 capital."""
import asyncio

from sqlalchemy import select

from utils import (
    DBSession, GREEN, BLUE, YELLOW, RED, NC,
    update_env_var, print_header
)

# Must import after utils sets up path
from src.models.bot import Bot, BotStatus
from src.models.user import User

DEFAULT_BOT_CONFIG = {
    "name": "0xBot",
    "model_name": "qwen-max",
    "initial_capital": 10000.00,
    "capital": 10000.00,
    "paper_trading": True,
    "trading_symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"],
    "risk_params": {
        "max_position_pct": 0.15,
        "max_exposure_pct": 0.85,
        "stop_loss_pct": 0.035,
        "take_profit_pct": 0.07,
    },
}


async def get_or_create_user(db) -> User:
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            email="test@0xbot.com",
            username="0xBot-Test",
            hashed_password="$2b$12$dummy_hash_for_testing",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"{GREEN}Created test user: {user.email}{NC}")

    return user


async def reset_bot(db, bot: Bot) -> Bot:
    bot.capital = 10000.00
    bot.initial_capital = 10000.00
    await db.commit()
    await db.refresh(bot)
    return bot


async def create_test_bot():
    async with DBSession() as db:
        user = await get_or_create_user(db)

        result = await db.execute(select(Bot).where(Bot.status == BotStatus.ACTIVE))
        existing_bot = result.scalar_one_or_none()

        if existing_bot:
            print(f"{YELLOW}Active bot exists:{NC}")
            print(f"  ID: {existing_bot.id}")
            print(f"  Name: {existing_bot.name}")
            print(f"  Capital: ${existing_bot.capital:,.2f}")

            response = input("\nReset this bot? (y/n): ").lower()
            if response != "y":
                print(f"{RED}Cancelled{NC}")
                return None

            bot = await reset_bot(db, existing_bot)
            print(f"{GREEN}Bot reset successfully!{NC}")
        else:
            bot = Bot(user_id=user.id, status=BotStatus.ACTIVE, **DEFAULT_BOT_CONFIG)
            db.add(bot)
            await db.commit()
            await db.refresh(bot)

            print(f"{GREEN}Bot created:{NC}")
            print(f"  ID: {bot.id}")
            print(f"  Name: {bot.name}")
            print(f"  Status: {bot.status.value}")
            print(f"  Capital: ${bot.capital:,.2f}")
            print(f"  Symbols: {', '.join(bot.trading_symbols)}")

        update_env_var("AUTO_START_BOT_ID", bot.id)
        print(f"\n{BLUE}Start the bot with: ./start.sh{NC}")
        return bot


if __name__ == "__main__":
    print_header("CREATE TEST BOT - $10,000")
    asyncio.run(create_test_bot())
