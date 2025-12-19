"""Test OKX API connection and demo mode."""

import os
import asyncio
from dotenv import load_dotenv
import ccxt.async_support as ccxt

# Load environment variables
load_dotenv()

async def test_okx_connection():
    """Test OKX connection with different configurations."""
    
    api_key = os.getenv("OKX_API_KEY")
    secret_key = os.getenv("OKX_SECRET_KEY")
    passphrase = os.getenv("OKX_PASSPHRASE")
    
    print("=" * 70)
    print("🔍 Testing OKX API Connection")
    print("=" * 70)
    print(f"API Key: {api_key[:8]}...{api_key[-4:] if api_key else 'None'}")
    print(f"Secret: {secret_key[:8]}...{secret_key[-4:] if secret_key else 'None'}")
    print(f"Passphrase: {'✓ Set' if passphrase else '✗ Missing'}")
    print()
    
    # Test 1: Public API (no auth)
    print("📊 Test 1: Public API (No Authentication)")
    try:
        exchange_public = ccxt.okx({
            'enableRateLimit': True,
        })
        ticker = await exchange_public.fetch_ticker('BTC/USDT:USDT')
        print(f"✅ Public API works! BTC price: ${ticker['last']:,.2f}")
        await exchange_public.close()
    except Exception as e:
        print(f"❌ Public API error: {e}")
    print()
    
    # Test 2: Demo mode with authentication
    print("🧪 Test 2: Demo Mode with Authentication")
    try:
        exchange_demo = ccxt.okx({
            'apiKey': api_key,
            'secret': secret_key,
            'password': passphrase,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',
                'demo': True,  # Enable demo mode
            }
        })
        
        # Try to fetch markets (requires auth in demo mode)
        print("Loading markets...")
        await exchange_demo.load_markets()
        print(f"✅ Demo mode authenticated! Markets loaded: {len(exchange_demo.markets)}")
        
        # Try to fetch balance
        print("Fetching demo balance...")
        balance = await exchange_demo.fetch_balance()
        print(f"✅ Demo balance: {balance.get('USDT', {}).get('free', 0)} USDT")
        
        await exchange_demo.close()
    except Exception as e:
        print(f"❌ Demo mode error: {e}")
        print(f"Error type: {type(e).__name__}")
    print()
    
    # Test 3: Check if API key is for demo or live
    print("🔍 Test 3: API Key Environment Check")
    print("Note: OKX requires separate API keys for demo and live trading")
    print("- Demo keys are created in: https://www.okx.com/account/my-api (with 'Demo trading' option)")
    print("- Your keys must be created specifically for demo trading")
    print()

if __name__ == "__main__":
    asyncio.run(test_okx_connection())