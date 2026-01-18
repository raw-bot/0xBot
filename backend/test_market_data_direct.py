#!/usr/bin/env python3
"""Test market data fetching directly."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from src.core.exchange_client import ExchangeClient
from src.services.market_data_service import MarketDataService

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

async def test_market_data():
    """Test market data fetching."""
    print("=" * 80)
    print("MARKET DATA FETCH TEST")
    print("=" * 80)

    # Test with OKX sandbox (paper_trading=False)
    exchange = ExchangeClient(paper_trading=False)
    market_service = MarketDataService(exchange)

    symbols = ["BTC/USDT", "ETH/USDT"]

    for symbol in symbols:
        print(f"\n{'─' * 80}")
        print(f"Testing symbol: {symbol}")
        print(f"{'─' * 80}")

        # Test ticker
        try:
            print(f"Fetching ticker...")
            ticker = await market_service.fetch_ticker(symbol)
            print(f"✓ Ticker: {ticker.symbol} @ {ticker.last}")
        except Exception as e:
            print(f"✗ Ticker Error: {type(e).__name__}: {str(e)[:150]}")
            import traceback
            traceback.print_exc()

        # Test OHLCV
        try:
            print(f"Fetching OHLCV...")
            ohlcv = await market_service.fetch_ohlcv(symbol, timeframe="1h", limit=10)
            print(f"✓ OHLCV: Got {len(ohlcv)} candles")
            if ohlcv:
                print(f"  Latest close: {ohlcv[-1].close}")
        except Exception as e:
            print(f"✗ OHLCV Error: {type(e).__name__}: {str(e)[:150]}")
            import traceback
            traceback.print_exc()

    await exchange.exchange.close()
    print(f"\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_market_data())
