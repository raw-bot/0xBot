import asyncio
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.services.multi_coin_prompt_service import MultiCoinPromptService


async def test_prompt_generation():
    print("🧪 Testing MultiCoinPromptService Prompt Generation...")

    service = MultiCoinPromptService()

    # Mock Data
    bot = type(
        "Bot",
        (),
        {"id": "test_bot", "name": "Test Bot", "trading_symbols": ["BTC/USDT", "ETH/USDT"]},
    )

    all_coins_data = {
        "BTC/USDT": {
            "current_price": 92000.0,
            "funding_rate": 0.0001,
            "open_interest": {"latest": 5000000},
            "technical_indicators": {
                "5m": {"rsi14": 45.0, "macd": 10.0},
                "1h": {"rsi14": 60.0, "macd": 50.0},  # Mock 4h/1h data
            },
        },
        "ETH/USDT": {
            "current_price": 3200.0,
            "funding_rate": 0.0002,
            "open_interest": {"latest": 2000000},
            "technical_indicators": {
                "5m": {"rsi14": 30.0, "macd": -5.0},
                "1h": {"rsi14": 40.0, "macd": -10.0},
            },
        },
    }

    all_positions = [
        {
            "symbol": "BTC/USDT",
            "side": "LONG",
            "entry_price": 91000.0,
            "current_price": 92000.0,
            "size": 0.1,
            "unrealized_pnl_pct": 1.1,
        }
    ]

    portfolio_state = {"cash": 5000.0, "total_value": 15000.0}

    news_data = [
        {"title": "Bitcoin Hits $100k", "source": "CoinDesk", "time": "10m ago"},
        {"title": "ETH Upgrade Successful", "source": "Decrypt", "time": "1h ago"},
    ]

    # Generate Prompt
    result = service.get_multi_coin_decision(
        bot=bot,
        all_coins_data=all_coins_data,
        all_positions=all_positions,
        portfolio_state=portfolio_state,
        news_data=news_data,
    )

    prompt = result["prompt"]

    print("\n✅ Prompt Generated Successfully!")
    print("-" * 50)
    print(prompt)
    print("-" * 50)

    # Verification
    if "## 1. NARRATIVE vs REALITY CHECK" in prompt:
        print("✅ Section 'NARRATIVE vs REALITY CHECK' found.")
    else:
        print("❌ Section 'NARRATIVE vs REALITY CHECK' MISSING.")

    if "Bitcoin Hits $100k" in prompt:
        print("✅ News item found.")
    else:
        print("❌ News item MISSING.")

    if "## 2. GLOBAL STRUCTURE (4h Timeframe)" in prompt:
        print("✅ Section 'GLOBAL STRUCTURE' found.")
    else:
        print("❌ Section 'GLOBAL STRUCTURE' MISSING.")

    if "UPTREND" in prompt or "DOWNTREND" in prompt or "NEUTRAL" in prompt:
        print("✅ Trend analysis found.")


if __name__ == "__main__":
    asyncio.run(test_prompt_generation())
