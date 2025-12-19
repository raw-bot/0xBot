"""Test spécifique pour les clés API Demo OKX."""

import os
import asyncio
from dotenv import load_dotenv
import ccxt.async_support as ccxt

load_dotenv()

async def test_demo_keys():
    """Test des clés demo OKX avec différentes configurations."""
    
    api_key = os.getenv("OKX_API_KEY")
    secret_key = os.getenv("OKX_SECRET_KEY")
    passphrase = os.getenv("OKX_PASSPHRASE")
    
    print("=" * 80)
    print("🧪 TEST DES CLÉS DEMO OKX")
    print("=" * 80)
    print()
    
    # Configuration 1: Mode demo avec URLs demo explicites
    print("Test 1: Mode demo avec URLs demo")
    print("-" * 80)
    try:
        exchange = ccxt.okx({
            'apiKey': api_key,
            'secret': secret_key,
            'password': passphrase,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',
            },
            'urls': {
                'api': {
                    'public': 'https://www.okx.com',
                    'private': 'https://www.okx.com',
                }
            }
        })
        
        # Activer le mode sandbox/demo
        exchange.set_sandbox_mode(True)
        
        print("Tentative de chargement des marchés...")
        await exchange.load_markets()
        print("✅ Marchés chargés!")
        
        print("Tentative de récupération de la balance...")
        balance = await exchange.fetch_balance()
        print(f"✅ Balance récupérée: {balance.get('USDT', {}).get('free', 0)} USDT")
        
        await exchange.close()
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
    print()
    
    # Configuration 2: Sans mode demo, en live
    print("Test 2: Mode LIVE (sans demo)")
    print("-" * 80)
    try:
        exchange = ccxt.okx({
            'apiKey': api_key,
            'secret': secret_key,
            'password': passphrase,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',
            }
        })
        
        print("Tentative de récupération du compte...")
        account_info = await exchange.fetch_balance()
        print(f"✅ Compte actif! USDT: {account_info.get('USDT', {}).get('free', 0)}")
        
        await exchange.close()
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Erreur: {error_msg}")
        
        if "50119" in error_msg:
            print()
            print("💡 ANALYSE:")
            print("  Vos clés 'OKXDemoTrade' ne fonctionnent ni en mode demo ni en mode live")
            print()
            print("  📋 ÉTAPES À SUIVRE:")
            print("  1. Allez sur https://www.okx.com/trade-demo")
            print("  2. Activez votre compte demo trading si ce n'est pas déjà fait")
            print("  3. Attendez quelques minutes (propagation des clés)")
            print("  4. Retestez")
            print()
            print("  OU")
            print()
            print("  Créez de nouvelles clés API depuis:")
            print("  - Compte DEMO: https://www.okx.com/account/my-api (en mode demo)")
            print("  - Compte LIVE: https://www.okx.com/account/my-api (en mode normal)")
    print()
    
    print("=" * 80)
    print("📊 CONCLUSION")
    print("=" * 80)
    print()
    print("Pour le moment, votre bot fonctionne parfaitement en mode paper trading")
    print("avec l'API publique OKX (sans authentification).")
    print()
    print("Les clés API ne sont nécessaires que pour:")
    print("  - Passer des ordres réels en mode LIVE")
    print("  - Consulter votre balance/positions")
    print()
    print("En mode paper trading actuel:")
    print("  ✅ Données de marché réelles (API publique)")
    print("  ✅ Trades simulés en base de données")
    print("  ✅ Aucune clé API nécessaire")
    print()

if __name__ == "__main__":
    asyncio.run(test_demo_keys())