import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.services.monk_mode_service import MonkModePromptService
from src.services.news_service import NewsService


async def test_news_integration():
    print("🧪 Testing News Integration...")

    # 1. Mock News Data
    mock_news = [
        {
            "title": "Bitcoin hits $100k",
            "source": "CoinDesk",
            "time": "5m ago",
            "currencies": ["BTC"],
            "url": "http://example.com",
        },
        {
            "title": "Solana network upgrade",
            "source": "Twitter",
            "time": "1h ago",
            "currencies": ["SOL"],
            "url": "http://example.com",
        },
    ]

    # 2. Initialize Service
    service = MonkModePromptService()

    # 3. Mock Inputs
    bot = MagicMock()
    all_coins_data = {"BTC/USDT": {"snapshot": {"current_price": 100000}}}
    all_positions = []
    portfolio_state = {"cash": 10000}

    # 4. Generate Prompt with News
    print("📝 Generating prompt with news...")
    decision = service.get_monk_mode_decision(
        bot=bot,
        all_coins_data=all_coins_data,
        all_positions=all_positions,
        portfolio_state=portfolio_state,
        news_data=mock_news,
    )

    prompt = decision["prompt"]

    # 5. Verify Content
    print("\n🔍 Verifying Prompt Content:")

    if "2. Narrative vs Reality Check (CryptoPanic News)" in prompt:
        print("✅ Section Header Found")
    else:
        print("❌ Section Header Missing")

    if "Bitcoin hits $100k" in prompt:
        print("✅ BTC News Found")
    else:
        print("❌ BTC News Missing")

    if "Solana network upgrade" in prompt:
        print("✅ SOL News Found")
    else:
        print("❌ SOL News Missing")

    # Print snippet
    start = prompt.find("2. Narrative")
    end = prompt.find("3. FOMO")
    print("\n📄 Prompt Snippet:")
    print(prompt[start:end])


if __name__ == "__main__":
    asyncio.run(test_news_integration())
