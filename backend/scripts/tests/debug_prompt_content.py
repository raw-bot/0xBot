#!/usr/bin/env python3
"""
Script de diagnostic pour voir EXACTEMENT ce que Qwen reçoit
"""
import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from src.core.database import AsyncSessionLocal
from src.models.bot import Bot
from src.services.market_data_service import MarketDataService
from src.services.multi_coin_prompt_service import MultiCoinPromptService
from src.services.market_analysis_service import MarketAnalysisService

async def main():
    print("\n" + "="*80)
    print("🔍 DIAGNOSTIC: Contenu du prompt envoyé à Qwen")
    print("="*80 + "\n")

    async with AsyncSessionLocal() as db:
        # Get first bot (any status)
        result = await db.execute(select(Bot).limit(1))
        bot = result.scalar_one_or_none()

        if not bot:
            print("❌ Aucun bot trouvé dans la base de données")
            return

        print(f"ℹ️  Bot Status: {bot.status}")
        if bot.status != "active":
            print(f"⚠️  Note: Bot is {bot.status}, not active")

        print(f"✅ Bot trouvé: {bot.name}")
        print(f"   Symbols: {bot.trading_symbols}")

        # Fetch market data for first symbol
        symbol = bot.trading_symbols[0]
        print(f"\n📊 Fetching data for {symbol}...")

        market_service = MarketDataService()

        # Get market snapshot with multi-timeframe
        snapshot = await market_service.get_market_data_multi_timeframe(
            symbol=symbol,
            timeframe_short="5m",
            timeframe_long="1h"
        )

        print(f"\n📈 Market Data Retrieved:")
        print(f"   Current Price: ${snapshot['current_price']:,.2f}")
        print(f"   Funding Rate: {snapshot.get('funding_rate', 'N/A')}")

        # Print technical indicators
        tech_5m = snapshot['technical_indicators']['5m']
        tech_1h = snapshot['technical_indicators']['1h']

        print(f"\n📊 Technical Indicators (5m):")
        print(f"   RSI(7): {tech_5m.get('rsi7', 'N/A')}")
        print(f"   RSI(14): {tech_5m.get('rsi14', 'N/A')}")
        print(f"   EMA(20): {tech_5m.get('ema20', 'N/A')}")
        print(f"   EMA(50): {tech_5m.get('ema50', 'N/A')}")
        print(f"   MACD: {tech_5m.get('macd', 'N/A')}")

        print(f"\n📊 Technical Indicators (1h):")
        print(f"   RSI(14): {tech_1h.get('rsi14', 'N/A')}")
        print(f"   EMA(20): {tech_1h.get('ema20', 'N/A')}")
        print(f"   EMA(50): {tech_1h.get('ema50', 'N/A')}")

        # Get all coins data using the SAME method as trading engine
        print(f"\n🌐 Fetching all coins data (complete snapshots)...")
        all_coins = {}
        for sym in bot.trading_symbols[:3]:  # Limit to 3 for brevity
            try:
                # Fetch COMPLETE snapshot like the real trading engine does
                coin_snapshot = await market_service.get_market_data_multi_timeframe(
                    symbol=sym,
                    timeframe_short="5m",
                    timeframe_long="1h"
                )
                all_coins[sym] = coin_snapshot

                # Display summary
                price = coin_snapshot['current_price']
                tech_5m = coin_snapshot['technical_indicators']['5m']
                rsi = tech_5m.get('rsi14', 50)
                ema20 = tech_5m.get('ema20', 0)
                print(f"   ✓ {sym}: ${price:,.2f} | RSI: {rsi:.1f} | EMA20: {ema20:.2f}")
            except Exception as e:
                print(f"   ✗ {sym}: Error - {e}")

        # Get market regime
        print(f"\n🎯 Analyzing market regime...")
        market_context = {
            'regime': {
                'regime': 'NEUTRAL',
                'confidence': 0.5
            },
            'breadth': {
                'advancing': 2,
                'declining': 1
            }
        }

        # Build enriched prompt
        print(f"\n🧠 Building enriched prompt...")
        prompt_service = MultiCoinPromptService(db)

        prompt_data = prompt_service.get_simple_decision(
            bot=bot,
            symbol=symbol,
            market_snapshot=snapshot,
            market_regime=market_context,
            all_coins_data=all_coins,
            bot_positions=[]
        )

        prompt = prompt_data['prompt']

        print("\n" + "="*80)
        print("📄 PROMPT COMPLET ENVOYÉ À QWEN")
        print("="*80)
        print(prompt)
        print("="*80)

        # Extract key values from prompt to verify
        print("\n🔍 VÉRIFICATION DES VALEURS DANS LE PROMPT:")
        print("-" * 80)

        if f"current_rsi (7 period) = N/A" in prompt:
            print("⚠️  RSI(7) marqué comme N/A dans le prompt")
        elif "current_rsi (7 period) =" in prompt:
            import re
            match = re.search(r'current_rsi \(7 period\) = ([0-9.]+)', prompt)
            if match:
                print(f"✅ RSI(7) dans le prompt: {match.group(1)}")

        if f"current_rsi (14 period) = N/A" in prompt:
            print("⚠️  RSI(14) marqué comme N/A dans le prompt")
        elif "current_rsi (14 period) =" in prompt:
            import re
            match = re.search(r'current_rsi \(14 period\) = ([0-9.]+)', prompt)
            if match:
                print(f"✅ RSI(14) dans le prompt: {match.group(1)}")

        if "current_ema20 =" in prompt:
            import re
            match = re.search(r'current_ema20 = ([0-9.]+)', prompt)
            if match:
                print(f"✅ EMA(20) dans le prompt: {match.group(1)}")

        print("\n" + "="*80)
        print("🎯 DIAGNOSTIC TERMINÉ")
        print("="*80)
        print("\nAnalyse:")
        print("1. Si les valeurs RSI/EMA dans le prompt sont 0 ou 50 → Problème de calcul")
        print("2. Si les valeurs sont correctes mais Qwen répond 'insufficient data' → Problème de prompt")
        print("3. Comparez les valeurs affichées plus haut avec celles dans le prompt")
        print("\n")

if __name__ == "__main__":
    asyncio.run(main())
