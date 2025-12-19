"""Diagnostic détaillé des clés API OKX."""

import os
import asyncio
from dotenv import load_dotenv
import ccxt.async_support as ccxt

# Load environment variables
load_dotenv()

async def diagnose_okx_api():
    """Diagnostic complet des clés API OKX."""
    
    api_key = os.getenv("OKX_API_KEY")
    secret_key = os.getenv("OKX_SECRET_KEY")
    passphrase = os.getenv("OKX_PASSPHRASE")
    
    print("=" * 80)
    print("🔍 DIAGNOSTIC DES CLÉS API OKX")
    print("=" * 80)
    print()
    
    # 1. Vérifier que les clés existent
    print("📋 1. Vérification des variables d'environnement")
    print("-" * 80)
    print(f"OKX_API_KEY: {'✅ Présente' if api_key else '❌ Manquante'}")
    if api_key:
        print(f"  Format: {api_key[:12]}...{api_key[-8:]}")
    print(f"OKX_SECRET_KEY: {'✅ Présente' if secret_key else '❌ Manquante'}")
    if secret_key:
        print(f"  Format: {secret_key[:8]}...{secret_key[-8:]}")
    print(f"OKX_PASSPHRASE: {'✅ Présente' if passphrase else '❌ Manquante'}")
    if passphrase:
        print(f"  Longueur: {len(passphrase)} caractères")
    print()
    
    # 2. Test en mode LIVE
    print("🔴 2. Test avec LIVE API (vos clés actuelles)")
    print("-" * 80)
    try:
        exchange_live = ccxt.okx({
            'apiKey': api_key,
            'secret': secret_key,
            'password': passphrase,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',
            }
        })
        
        print("Tentative de récupération du compte...")
        account = await exchange_live.fetch_balance()
        print("✅ SUCCÈS! Vos clés fonctionnent en mode LIVE")
        print(f"Compte: {account.get('info', {}).get('uid', 'N/A')}")
        
        # Check balances
        usdt_balance = account.get('USDT', {})
        print(f"Balance USDT: {usdt_balance.get('free', 0)} USDT")
        
        await exchange_live.close()
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ ÉCHEC en mode LIVE")
        print(f"Erreur: {error_msg}")
        
        if "50119" in error_msg or "doesn't exist" in error_msg:
            print()
            print("⚠️  DIAGNOSTIC:")
            print("  Vos clés API ne sont pas valides ou ont été désactivées")
            print()
            print("  Raisons possibles:")
            print("  1. Les clés ont été créées mais pas encore activées (attendez quelques minutes)")
            print("  2. Les clés ont été révoquées depuis OKX")
            print("  3. L'adresse IP n'est pas dans la whitelist (si configurée)")
            print("  4. Les permissions ne sont pas correctes")
        
        elif "50113" in error_msg or "Invalid sign" in error_msg:
            print()
            print("⚠️  DIAGNOSTIC:")
            print("  Le SECRET_KEY ou le PASSPHRASE est incorrect")
            print("  Vérifiez que vous avez copié/collé correctement")
    print()
    
    # 3. Test en mode DEMO
    print("🧪 3. Test avec DEMO API")
    print("-" * 80)
    print("Note: OKX nécessite des clés API SÉPARÉES pour le mode démo")
    print()
    try:
        exchange_demo = ccxt.okx({
            'apiKey': api_key,
            'secret': secret_key,
            'password': passphrase,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',
                'demo': True,
            }
        })
        
        print("Tentative de récupération du compte DEMO...")
        await exchange_demo.load_markets()
        print("✅ SUCCÈS! Vos clés fonctionnent en mode DEMO")
        
        await exchange_demo.close()
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ ÉCHEC en mode DEMO")
        print(f"Erreur: {error_msg}")
        
        if "50119" in error_msg:
            print()
            print("⚠️  DIAGNOSTIC:")
            print("  Vos clés sont pour le compte LIVE, pas pour le compte DEMO")
            print()
            print("  💡 SOLUTION:")
            print("  Pour utiliser le mode démo OKX, vous devez:")
            print("  1. Créer un compte démo sur OKX (séparé du compte live)")
            print("  2. Créer des clés API spécifiques pour ce compte démo")
            print("  3. Remplacer les clés dans le .env")
            print()
            print("  OU (recommandé pour le paper trading):")
            print("  Utilisez l'API publique sans authentification")
            print("  → C'est ce que le bot fait actuellement en mode paper_trading")
    print()
    
    # 4. Recommandation finale
    print("=" * 80)
    print("📊 RECOMMANDATION")
    print("=" * 80)
    print()
    print("Pour le PAPER TRADING (simulation):")
    print("  ✅ Utilisez l'API publique (pas besoin de clés)")
    print("  ✅ C'est ce que votre bot fait actuellement")
    print("  ✅ Données réelles + trades simulés en DB")
    print()
    print("Pour le LIVE TRADING (argent réel):")
    print("  1. Vérifiez que vos clés LIVE fonctionnent (test ci-dessus)")
    print("  2. Activez les permissions: Read + Trade (PAS Withdraw)")
    print("  3. Configurez paper_trading=False dans le bot")
    print()

if __name__ == "__main__":
    asyncio.run(diagnose_okx_api())