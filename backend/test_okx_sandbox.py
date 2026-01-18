#!/usr/bin/env python3
"""Test OKX sandbox and different configurations."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
import ccxt.async_support as ccxt

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

async def test_okx_configs():
    """Test different OKX configurations."""
    print("=" * 80)
    print("OKX CONFIGURATION TEST")
    print("=" * 80)

    api_key = os.getenv("OKX_API_KEY", "")
    secret = os.getenv("OKX_SECRET_KEY", "")
    passphrase = os.getenv("OKX_PASSPHRASE", "")

    configs = [
        {
            "name": "Sandbox (Default Type: Spot)",
            "params": {
                "enableRateLimit": True,
                "options": {"defaultType": "spot", "sandboxMode": True},
                "apiKey": api_key,
                "secret": secret,
                "password": passphrase,
            }
        },
        {
            "name": "Sandbox (Default Type: Swap)",
            "params": {
                "enableRateLimit": True,
                "options": {"defaultType": "swap", "sandboxMode": True},
                "apiKey": api_key,
                "secret": secret,
                "password": passphrase,
            }
        },
        {
            "name": "Live (Default Type: Spot)",
            "params": {
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
                "apiKey": api_key,
                "secret": secret,
                "password": passphrase,
            }
        },
        {
            "name": "Live (Default Type: Swap)",
            "params": {
                "enableRateLimit": True,
                "options": {"defaultType": "swap"},
                "apiKey": api_key,
                "secret": secret,
                "password": passphrase,
            }
        },
        {
            "name": "Public (No Auth) - Spot",
            "params": {
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            }
        },
        {
            "name": "Public (No Auth) - Swap",
            "params": {
                "enableRateLimit": True,
                "options": {"defaultType": "swap"},
            }
        },
    ]

    for config in configs:
        print(f"\n{'─' * 80}")
        print(f"Testing: {config['name']}")
        print(f"{'─' * 80}")

        exchange = ccxt.okx(config['params'])

        try:
            # Try to load markets
            markets = await exchange.load_markets()
            print(f"✓ Markets loaded: {len(markets)} markets available")

            # Try to fetch a specific symbol
            symbol = "BTC/USDT"
            if symbol in markets:
                ticker = await exchange.fetch_ticker(symbol)
                print(f"✓ Ticker fetch successful for {symbol}")
                print(f"  Last price: {ticker.get('last')}")
            else:
                # Try alternative format
                symbol = "BTC/USDT:USDT"
                if symbol in markets:
                    ticker = await exchange.fetch_ticker(symbol)
                    print(f"✓ Ticker fetch successful for {symbol}")
                    print(f"  Last price: {ticker.get('last')}")
                else:
                    print(f"✗ Neither BTC/USDT nor BTC/USDT:USDT found in markets")
                    # Show what symbols are available
                    btc_symbols = [s for s in markets.keys() if 'BTC' in s][:3]
                    print(f"  Available BTC symbols: {btc_symbols}")

        except ccxt.AuthenticationError as e:
            print(f"✗ Authentication Error: {str(e)[:120]}")
        except ccxt.ExchangeError as e:
            print(f"✗ Exchange Error: {str(e)[:120]}")
        except Exception as e:
            print(f"✗ Error: {type(e).__name__}: {str(e)[:120]}")
        finally:
            await exchange.close()

    print(f"\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_okx_configs())
