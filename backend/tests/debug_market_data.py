import asyncio
import os
import sys

from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Load env vars
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from src.core.exchange_client import get_exchange_client
from src.services.market_data_service import MarketDataService


async def debug_market_data():
    print("🔍 Debugging Market Data...")

    try:
        # 1. Initialize Exchange
        exchange = get_exchange_client()
        # await exchange.initialize() # Not needed
        print(
            f"✅ Exchange initialized: {exchange.exchange_id if hasattr(exchange, 'exchange_id') else 'OKX'}"
        )

        # 2. Initialize Service
        service = MarketDataService(exchange)
        symbol = "BTC/USDT"

        # 3. Fetch Ticker
        print(f"\n📊 Fetching Ticker for {symbol}...")
        try:
            raw_ticker = await exchange.fetch_ticker(symbol)
            print(f"Raw Ticker Keys: {list(raw_ticker.keys())}")
            print(f"Last Price: {raw_ticker.get('last')}")
            print(f"Bid: {raw_ticker.get('bid')}")
            print(f"Ask: {raw_ticker.get('ask')}")

            ticker = await service.fetch_ticker(symbol)
            print(f"Parsed Ticker: {ticker}")
        except Exception as e:
            print(f"❌ Error fetching ticker: {e}")

        # 4. Fetch OHLCV
        print(f"\n🕯️ Fetching OHLCV for {symbol}...")
        try:
            ohlcv = await service.fetch_ohlcv(symbol, limit=5)
            print(f"Fetched {len(ohlcv)} candles")
            if ohlcv:
                print(f"Last Candle: {ohlcv[-1]}")
        except Exception as e:
            print(f"❌ Error fetching OHLCV: {e}")

    except Exception as e:
        print(f"❌ Critical Error: {e}")
    finally:
        if "exchange" in locals():
            await exchange.close()
            print("\n🔒 Exchange connection closed")


if __name__ == "__main__":
    asyncio.run(debug_market_data())
