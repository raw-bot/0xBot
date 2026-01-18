#!/usr/bin/env python3
"""Debug _fetch_symbol step by step."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from src.core.config import config
from src.services.market_data_service import MarketDataService
from src.core.exchange_client import ExchangeClient

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

async def test_fetch_symbol_steps():
    """Test each step of _fetch_symbol."""
    print("=" * 80)
    print("DEBUGGING _FETCH_SYMBOL STEPS")
    print("=" * 80)

    exchange = ExchangeClient(paper_trading=False)
    market_service = MarketDataService(exchange)

    symbol = "BTC/USDT"

    # Step 1: Fetch ticker
    print(f"\n1. Fetching ticker for {symbol}...")
    try:
        ticker = await market_service.fetch_ticker(symbol)
        print(f"   ✓ Ticker fetched")
        print(f"   Type: {type(ticker)}")
        print(f"   Ticker: {ticker}")
        print(f"   Ticker truthy: {bool(ticker)}")
        print(f"   Ticker.last: {ticker.last if ticker else 'N/A'}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return

    # Step 2: Fetch OHLCV 1h
    print(f"\n2. Fetching OHLCV 1h ({symbol})...")
    try:
        ohlcv_1h = await market_service.fetch_ohlcv(symbol, timeframe="1h", limit=250)
        print(f"   ✓ OHLCV fetched")
        print(f"   Type: {type(ohlcv_1h)}")
        print(f"   Length: {len(ohlcv_1h) if ohlcv_1h else 'None'}")
        print(f"   First candle: {ohlcv_1h[0] if ohlcv_1h else 'N/A'}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return

    # Step 3: Fetch OHLCV 4h
    print(f"\n3. Fetching OHLCV 4h ({symbol})...")
    try:
        ohlcv_4h = await market_service.fetch_ohlcv(symbol, timeframe="4h", limit=20)
        print(f"   ✓ OHLCV fetched")
        print(f"   Length: {len(ohlcv_4h) if ohlcv_4h else 'None'}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return

    # Step 4: Create MarketSnapshot
    print(f"\n4. Creating MarketSnapshot...")
    try:
        from src.blocks.block_market_data import MarketSnapshot
        from decimal import Decimal

        snapshot = MarketSnapshot(
            symbol=symbol,
            price=Decimal(str(ticker.last)),
            change_24h=ticker.percentage or 0,
            volume_24h=ticker.quote_volume or 0,
        )
        print(f"   ✓ MarketSnapshot created")
        print(f"   Symbol: {snapshot.symbol}")
        print(f"   Price: {snapshot.price}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return

    print(f"\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_fetch_symbol_steps())
