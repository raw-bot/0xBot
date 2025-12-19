import asyncio
import sys
import uuid
from decimal import Decimal
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from src.core.config import config
from src.core.database import AsyncSessionLocal
from src.models.bot import Bot, BotStatus
from src.models.user import User
from src.services.position_service import PositionService
from src.services.trade_executor_service import TradeExecutorService


async def verify_leverage_fix():
    print("🧪 Verifying Leverage Fix...")
    print("=" * 50)

    async with AsyncSessionLocal() as db:
        # 0. Get User
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()

        if not user:
            print("⚠️  No user found, creating test user...")
            user = User(email="test_leverage@example.com", password_hash="hash")
            db.add(user)
            await db.commit()
            await db.refresh(user)

        print(f"👤 Using user: {user.email}")

        # 1. Setup Test Bot
        bot_id = uuid.uuid4()
        initial_capital = Decimal("10000.0")
        bot = Bot(
            id=bot_id,
            name="Test Bot Leverage",
            user_id=user.id,
            model_name="deepseek-chat",
            status=BotStatus.ACTIVE,
            initial_capital=initial_capital,
            capital=initial_capital,
            risk_params={
                "leverage": 10.0
            },  # Store in risk_params if needed, though logic uses config.DEFAULT_LEVERAGE
        )
        db.add(bot)
        await db.commit()
        print(f"✅ Created test bot with ${initial_capital}")

        # 2. Setup Services
        trade_executor = TradeExecutorService(db)
        position_service = PositionService(db)

        # 3. Execute Entry with 10x Leverage
        # Mock decision
        entry_price = Decimal("50000.0")
        quantity = Decimal("0.1")  # $5000 value
        # Margin should be $5000 / 10 = $500

        # Ensure config is 10x
        original_leverage = config.DEFAULT_LEVERAGE
        config.DEFAULT_LEVERAGE = 10.0
        print(f"ℹ️  Configured Global Leverage: {config.DEFAULT_LEVERAGE}x")

        decision = {
            "symbol": "BTC/USDT",
            "side": "long",
            "size_pct": 0.5,  # Irrelevant as we force quantity in logic but here used for calc
            "entry_price": float(entry_price),
            "stop_loss": float(entry_price * Decimal("0.9")),
            "take_profit": float(entry_price * Decimal("1.1")),
            "confidence": 0.9,
        }

        # We need to bypass calculate_position_size to force specific quantity for easy math?
        # Or just let it calculate and check the math.
        # Let's use execute_entry but we can't easily force quantity there without mocking RiskManager.
        # However, we can check the result.

        # Actually, execute_entry calls RiskManager.calculate_position_size.
        # Let's just call execute_entry and see what happens.
        # We need to make sure it buys something.

        print("🚀 Executing Entry...")
        position, trade = await trade_executor.execute_entry(bot, decision, entry_price)

        if not position:
            print("❌ Entry failed")
            return

        print(f"✅ Position opened: {position.quantity} BTC @ ${position.entry_price}")
        print(f"   Stored Leverage: {position.leverage}x")

        # Verify Leverage is stored
        if position.leverage != Decimal("10.0"):
            print(f"❌ FAIL: Stored leverage is {position.leverage}, expected 10.0")
            return
        else:
            print("✅ PASS: Leverage 10.0 correctly stored in DB")

        # Check Capital Deduction
        # Margin = (Price * Qty) / 10
        # Fees = (Price * Qty) * 0.001 (Paper trading fee)
        expected_margin = (position.entry_price * position.quantity) / Decimal("10.0")
        expected_fees = (position.entry_price * position.quantity) * Decimal("0.001")
        expected_capital = initial_capital - expected_margin - expected_fees

        # Reload bot
        await db.refresh(bot)
        print(f"   Capital after entry: ${bot.capital:.2f}")
        print(f"   Expected: ${expected_capital:.2f}")

        if abs(bot.capital - expected_capital) > Decimal("0.01"):
            print(f"❌ FAIL: Capital calculation mismatch on entry")
        else:
            print("✅ PASS: Capital correctly deducted based on 10x leverage")

        # 4. Change Global Config to 5x
        config.DEFAULT_LEVERAGE = 5.0
        print(f"\n🔄 Changed Global Leverage to: {config.DEFAULT_LEVERAGE}x")

        # 5. Execute Exit
        print("🚀 Executing Exit...")
        # Assume price didn't change for simplicity, just checking margin release
        exit_price = entry_price

        await trade_executor.execute_exit(position, exit_price, reason="test_verification")

        # Reload bot
        await db.refresh(bot)

        # Check Capital Restoration
        # Should use stored leverage (10x), NOT global config (5x)
        # Released Margin = (Entry Price * Qty) / 10
        # PnL = 0 (since exit_price = entry_price)
        # Exit Fees = (Exit Price * Qty) * 0.001

        expected_margin_release = (position.entry_price * position.quantity) / Decimal("10.0")
        expected_exit_fees = (exit_price * position.quantity) * Decimal("0.001")

        # Final Capital = Capital_After_Entry + Margin_Release + PnL - Exit_Fees
        # PnL is 0 here (ignoring fees which are separate)
        # Actually calculate_realized_pnl returns (Exit - Entry) * Qty - Fees?
        # No, execute_exit calculates realized_pnl = (diff) * qty - fees.
        # And adds: bot.capital += margin_released + realized_pnl

        # So:
        # Realized PnL = 0 - Exit_Fees
        # Added to Capital = Margin_Release + (0 - Exit_Fees)
        # Final Capital = (Initial - Margin - Entry_Fees) + Margin_Release - Exit_Fees
        # Final Capital = Initial - Entry_Fees - Exit_Fees

        expected_final_capital = initial_capital - expected_fees - expected_exit_fees

        print(f"   Final Capital: ${bot.capital:.2f}")
        print(f"   Expected (if 10x used): ${expected_final_capital:.2f}")

        # Calculate what it would be if 5x was used (BUG scenario)
        # If 5x used for release: Margin_Release = (Value) / 5 = 2 * (Value / 10)
        # So we would get back double the margin we put in -> Infinite Money Glitch
        wrong_margin_release = (position.entry_price * position.quantity) / Decimal("5.0")
        wrong_final_capital = expected_capital + wrong_margin_release - expected_exit_fees

        print(f"   Expected (if 5x BUG):   ${wrong_final_capital:.2f}")

        if abs(bot.capital - expected_final_capital) < Decimal("0.01"):
            print("✅ PASS: Correctly used stored 10x leverage for exit!")
        elif abs(bot.capital - wrong_final_capital) < Decimal("0.01"):
            print("❌ FAIL: Used global 5x leverage for exit (Bug still exists)")
        else:
            print(
                f"❌ FAIL: Unexpected capital value. Diff: {bot.capital - expected_final_capital}"
            )

        # Cleanup
        # await db.delete(bot) # Optional, maybe keep for inspection
        # await db.commit()

        # Restore config
        config.DEFAULT_LEVERAGE = original_leverage


if __name__ == "__main__":
    asyncio.run(verify_leverage_fix())
