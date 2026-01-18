#!/usr/bin/env python3
"""Debug script to test OKX market data fetching."""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
import ccxt.async_support as ccxt

# Load environment variables
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

async def test_okx_connection():
    """Test OKX connection and market data fetching."""
    print("=" * 80)
    print("OKX DEBUG TEST")
    print("=" * 80)

    # Test configuration
    exchange_options = {
        "enableRateLimit": True,
        "options": {"defaultType": "swap"},
        "apiKey": os.getenv("OKX_API_KEY", ""),
        "secret": os.getenv("OKX_SECRET_KEY", ""),
        "password": os.getenv("OKX_PASSPHRASE", ""),
    }

    print(f"\n1. Exchange options:")
    print(f"   API Key present: {bool(exchange_options['apiKey'])}")
    print(f"   Secret present: {bool(exchange_options['secret'])}")
    print(f"   Passphrase present: {bool(exchange_options['password'])}")
    print(f"   Default type: {exchange_options['options']['defaultType']}")

    # Initialize exchange
    exchange = ccxt.okx(exchange_options)

    try:
        # Test 1: Load markets
        print(f"\n2. Loading markets...")
        markets = await exchange.load_markets()
        print(f"   ✓ Loaded {len(markets)} markets")

        # Test 2: Check if specific symbols exist
        test_symbols = ["BTC/USDT:USDT", "BTC/USDT", "ETH/USDT:USDT", "ETH/USDT"]
        print(f"\n3. Checking symbol availability:")
        for symbol in test_symbols:
            exists = symbol in markets
            print(f"   {symbol}: {'✓' if exists else '✗'}")

        # Test 3: Try to fetch ticker for each symbol format
        print(f"\n4. Testing ticker fetch:")
        for symbol in ["BTC/USDT", "BTC/USDT:USDT"]:
            try:
                print(f"\n   Trying to fetch ticker for {symbol}...")
                ticker = await exchange.fetch_ticker(symbol)
                print(f"   ✓ Success! Last price: {ticker.get('last')}")
                break
            except Exception as e:
                print(f"   ✗ Failed: {type(e).__name__}: {str(e)[:100]}")

        # Test 4: Try to fetch OHLCV data
        print(f"\n5. Testing OHLCV fetch:")
        for symbol in ["BTC/USDT", "BTC/USDT:USDT"]:
            try:
                print(f"\n   Trying to fetch OHLCV for {symbol}...")
                ohlcv = await exchange.fetch_ohlcv(symbol, "1h", limit=10)
                print(f"   ✓ Success! Got {len(ohlcv)} candles")
                if ohlcv:
                    print(f"     Latest close: {ohlcv[-1][4]}")
                break
            except Exception as e:
                print(f"   ✗ Failed: {type(e).__name__}: {str(e)[:100]}")

        # Test 5: List first 10 swap symbols
        print(f"\n6. First 10 available symbols:")
        for i, symbol in enumerate(list(markets.keys())[:10]):
            print(f"   {symbol}")

    except Exception as e:
        print(f"\n✗ Connection error: {type(e).__name__}: {e}")
    finally:
        await exchange.close()
        print(f"\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_okx_connection())
