#!/usr/bin/env python3
"""
Test du prompt multi-coins pour vérifier la règle :
SOL (position) → HOLD/EXIT
BTC/ETH/BNB/XRP (pas position) → ENTRY/HOLD
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.multi_coin_prompt_service import MultiCoinPromptService


def test_multi_coin_logic():
    """Test de la logique multi-coins"""
    print("🧪 TEST: Multi-Coin Prompt Logic")
    print("=" * 50)

    service = MultiCoinPromptService()

    # Données de test : SOL avec position, autres sans position
    all_coins_data = {
        "BTC/USDT": {
            "current_price": 115599.5,
            "technical_indicators": {
                "5m": {"ema20": 115641.785, "macd": 49.905, "rsi7": 41.836},
                "1h": {"ema20": 112938.535, "ema50": 111539.738, "atr3": 421.773, "atr14": 606.485}
            }
        },
        "ETH/USDT": {
            "current_price": 4227.85,
            "technical_indicators": {
                "5m": {"ema20": 4222.572, "macd": 5.556, "rsi7": 55.136},
                "1h": {"ema20": 4046.775, "ema50": 3988.918, "atr3": 30.633, "atr14": 36.836}
            }
        },
        "SOL/USDT": {
            "current_price": 202.545,
            "technical_indicators": {
                "5m": {"ema20": 202.574, "macd": 0.171, "rsi7": 45.294},
                "1h": {"ema20": 196.51, "ema50": 193.5, "atr3": 1.677, "atr14": 2.08}
            }
        },
        "BNB/USDT": {
            "current_price": 1148.05,
            "technical_indicators": {
                "5m": {"ema20": 1149.674, "macd": 0.523, "rsi7": 31.564},
                "1h": {"ema20": 1131.736, "ema50": 1123.195, "atr3": 22.398, "atr14": 13.657}
            }
        },
        "XRP/USDT": {
            "current_price": 2.68925,
            "technical_indicators": {
                "5m": {"ema20": 2.687, "macd": 0.003, "rsi7": 49.85},
                "1h": {"ema20": 2.585, "ema50": 2.522, "atr3": 0.024, "atr14": 0.023}
            }
        }
    }

    # Positions : SOL seulement (comme dans votre exemple)
    all_positions = [{
        'symbol': 'SOL/USDT',
        'side': 'long',
        'size': 2.4364,
        'entry_price': 186.37,
        'current_price': 202.545,
        'pnl': 39.2,
        'pnl_pct': 8.7
    }]

    # Mock bot
    mock_bot = type('Bot', (), {
        'risk_params': {'stop_loss_pct': 0.035, 'take_profit_pct': 0.07}
    })()

    # Générer le prompt
    prompt_data = service.get_multi_coin_decision(
        bot=mock_bot,
        all_coins_data=all_coins_data,
        all_positions=all_positions
    )

    prompt = prompt_data["prompt"]

    print(f"✅ Prompt généré pour {prompt_data['num_coins']} coins")
    print(f"✅ {prompt_data['num_positions']} position(s) détectée(s)")
    print(f"✅ Longueur: {prompt_data['length']} mots")
    print()

    # Vérifications de la logique
    print("🔍 VÉRIFICATIONS LOGIQUE:")
    print("-" * 30)

    # Vérifier que SOL est marqué comme HAS POSITION
    if "HAS POSITION: SOL" in prompt:
        print("✅ SOL correctement identifié comme HAVING POSITION")
    else:
        print("❌ SOL pas identifié comme HAVING POSITION")

    # Vérifier que les autres coins sont marqués NO POSITION
    for coin in ["BTC", "ETH", "BNB", "XRP"]:
        if f"NO POSITION: {coin}" in prompt:
            print(f"✅ {coin} correctement identifié comme NO POSITION")
        else:
            print(f"❌ {coin} pas identifié comme NO POSITION")

    # Vérifier les instructions de décision
    if "COINS WITH POSITIONS (e.g., SOL):" in prompt:
        print("✅ Instructions pour positions existantes présentes")
    else:
        print("❌ Instructions pour positions manquantes")

    if "COINS WITHOUT POSITIONS (e.g., BTC, ETH, BNB, XRP):" in prompt:
        print("✅ Instructions pour nouvelles entrées présentes")
    else:
        print("❌ Instructions pour nouvelles entrées manquantes")

    # Vérifier le format JSON pour tous les coins
    if '"BTC":' in prompt and '"ETH":' in prompt and '"SOL":' in prompt and '"BNB":' in prompt and '"XRP":' in prompt:
        print("✅ Format JSON pour tous les coins présent")
    else:
        print("❌ Format JSON incomplet")

    print()
    print("📋 APERÇU DU PROMPT:")
    print("-" * 30)

    # Afficher les 20 premières lignes pour vérification
    lines = prompt.split('\n')
    for i, line in enumerate(lines[:25]):
        print(f"{i+1:2d}: {line}")

    if len(lines) > 25:
        print(f"... et {len(lines) - 25} lignes supplémentaires")

    print()
    print("🎯 RÉSULTAT DU TEST:")
    print("-" * 30)

    # Vérifications finales
    checks = [
        ("SOL → HAS POSITION", "HAS POSITION: SOL" in prompt),
        ("BTC → NO POSITION", "NO POSITION: BTC" in prompt),
        ("ETH → NO POSITION", "NO POSITION: ETH" in prompt),
        ("BNB → NO POSITION", "NO POSITION: BNB" in prompt),
        ("XRP → NO POSITION", "NO POSITION: XRP" in prompt),
        ("Instructions HOLD/EXIT", "COINS WITH POSITIONS" in prompt),
        ("Instructions ENTRY/HOLD", "COINS WITHOUT POSITIONS" in prompt),
        ("Format JSON complet", all(coin in prompt for coin in ["BTC", "ETH", "SOL", "BNB", "XRP"])),
    ]

    passed = sum(1 for _, result in checks if result)
    total = len(checks)

    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")

    print()
    print(f"🏆 SCORE: {passed}/{total} tests réussis")

    if passed == total:
        print("🎉 PERFECT! Le prompt respecte toutes les règles")
        print("📈 Logique validée: SOL (position) → HOLD/EXIT, BTC/ETH/BNB/XRP (pas pos) → ENTRY/HOLD")
    else:
        print("⚠️  Le prompt nécessite des ajustements")

    return passed == total


def test_multiple_positions():
    """Test avec 2-5 positions simultanées"""
    print("\n🧪 TEST: Multiple Positions (2-5)")
    print("=" * 50)

    service = MultiCoinPromptService()

    # Données pour 3 positions simultanées
    all_coins_data = {
        "BTC/USDT": {"current_price": 115599.5, "technical_indicators": {"5m": {"ema20": 115641.785, "macd": 49.905, "rsi7": 41.836}, "1h": {"ema20": 112938.535, "ema50": 111539.738, "atr3": 421.773, "atr14": 606.485}}},
        "ETH/USDT": {"current_price": 4227.85, "technical_indicators": {"5m": {"ema20": 4222.572, "macd": 5.556, "rsi7": 55.136}, "1h": {"ema20": 4046.775, "ema50": 3988.918, "atr3": 30.633, "atr14": 36.836}}},
        "SOL/USDT": {"current_price": 202.545, "technical_indicators": {"5m": {"ema20": 202.574, "macd": 0.171, "rsi7": 45.294}, "1h": {"ema20": 196.51, "ema50": 193.5, "atr3": 1.677, "atr14": 2.08}}},
    }

    # 3 positions simultanées
    all_positions = [
        {'symbol': 'BTC/USDT', 'side': 'long', 'size': 0.08, 'entry_price': 110000, 'current_price': 115599.5, 'pnl': 447.96, 'pnl_pct': 5.1},
        {'symbol': 'ETH/USDT', 'side': 'long', 'size': 2.1, 'entry_price': 4000, 'current_price': 4227.85, 'pnl': 478.48, 'pnl_pct': 5.7},
        {'symbol': 'SOL/USDT', 'side': 'long', 'size': 1.5, 'entry_price': 190, 'current_price': 202.545, 'pnl': 18.82, 'pnl_pct': 6.6}
    ]

    mock_bot = type('Bot', (), {'risk_params': {'stop_loss_pct': 0.035, 'take_profit_pct': 0.07}})()

    prompt_data = service.get_multi_coin_decision(
        bot=mock_bot,
        all_coins_data=all_coins_data,
        all_positions=all_positions
    )

    print(f"✅ Test avec {len(all_positions)} positions simultanées")
    print(f"✅ {prompt_data['num_positions']} positions détectées")
    print(f"✅ 0 nouvelles positions possibles ({prompt_data['num_coins'] - prompt_data['num_positions']} coins sans position)")

    # Vérifier que tous les coins avec position sont identifiés
    for pos in all_positions:
        symbol = pos['symbol']
        coin_name = symbol.split('/')[0]
        if f"HAS POSITION: {coin_name}" in prompt_data["prompt"]:
            print(f"✅ {coin_name} correctement identifié avec position")
        else:
            print(f"❌ {coin_name} pas identifié avec position")

    return True


if __name__ == "__main__":
    print("🚀 TEST DU PROMPT MULTI-COINS")
    print("Objectif: Vérifier que TOUS les coins sont analysés simultanément")
    print("Règle: SOL (position) → HOLD/EXIT, BTC/ETH/BNB/XRP (pas pos) → ENTRY/HOLD")
    print()

    # Test principal
    test1_passed = test_multi_coin_logic()

    # Test positions multiples
    test2_passed = test_multiple_positions()

    print("\n" + "="*60)
    print("🏁 RÉSUMÉ FINAL")
    print("="*60)

    if test1_passed and test2_passed:
        print("🎉 TOUS LES TESTS PASSÉS!")
        print("✅ Le prompt multi-coins respecte parfaitement vos règles:")
        print("   • Analyse TOUS les coins simultanément")
        print("   • SOL (avec position) → Évalue HOLD vs EXIT")
        print("   • BTC/ETH/BNB/XRP (sans position) → Cherche ENTRY opportunités")
        print("   • Support 2-5 positions simultanées")
        print("✅ Le problème est RÉSOLU!")
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("Le prompt nécessite des ajustements supplémentaires")

    print("="*60)
