import asyncio
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.services.news_service import NewsService


async def test_cryptocompare_parsing():
    print("🧪 Testing CryptoCompare News Service...")

    # Mock API Response
    mock_response_data = {
        "Data": [
            {
                "id": "123456",
                "guid": "http://example.com/news/1",
                "published_on": int(datetime.utcnow().timestamp()) - 600,  # 10 mins ago
                "imageurl": "http://example.com/image.jpg",
                "title": "Bitcoin Breaks $100k Barrier",
                "url": "http://example.com/news/1",
                "source": "CoinDesk",
                "body": "Bitcoin has finally reached...",
                "tags": "BTC|Market|Trading",
                "categories": "BTC|Market",
                "upvotes": "10",
                "downvotes": "2",
                "lang": "EN",
                "source_info": {
                    "name": "CoinDesk",
                    "lang": "EN",
                    "img": "http://example.com/logo.png",
                },
            }
        ],
        "Type": 100,
        "Message": "News list successfully returned",
        "Promoted": [],
    }

    # Mock config to have an API key
    with patch("src.core.config.config.CRYPTOCOMPARE_API_KEY", "mock_key"):
        service = NewsService()

        # Mock aiohttp session
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json.return_value = mock_response_data
            mock_get.return_value.__aenter__.return_value = mock_resp

            print("📝 Fetching news (mocked)...")
            news = await service.get_latest_news(["BTC/USDT"])

            print(f"✅ Fetched {len(news)} items")

            if len(news) > 0:
                item = news[0]
                print(f"🔍 First Item: {item}")

                # Verify fields
                if item["title"] == "Bitcoin Breaks $100k Barrier":
                    print("✅ Title parsed correctly")
                else:
                    print(f"❌ Title mismatch: {item['title']}")

                if item["source"] == "CoinDesk":
                    print("✅ Source parsed correctly")
                else:
                    print(f"❌ Source mismatch: {item['source']}")

                if "BTC" in item["currencies"]:
                    print("✅ Categories parsed correctly")
                else:
                    print(f"❌ Categories mismatch: {item['currencies']}")

                if (
                    "10m ago" in item["time"]
                    or "9m ago" in item["time"]
                    or "11m ago" in item["time"]
                ):
                    print("✅ Time parsed correctly")
                else:
                    print(f"❌ Time mismatch: {item['time']}")


if __name__ == "__main__":
    asyncio.run(test_cryptocompare_parsing())
