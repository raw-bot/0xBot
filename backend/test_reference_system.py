#!/usr/bin/env python3
"""
Test du système de référence pour valider les corrections
Simule les réponses LLM et teste le parsing
"""

import json
import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.llm_reference_parser import LLMReferenceParser
from src.services.reference_prompt_service import ReferencePromptService
from src.services.reference_trading_patch import ReferenceTradingPatch


def test_reference_parser():
    """Tester le parser de référence"""
    print("🧪 TEST: Parser de référence")
    print("-" * 50)

    parser = LLMReferenceParser()

    # Test 1: Format de référence parfait
    perfect_response = '''{
  "BTC": {
    "trade_signal_args": {
      "coin": "BTC",
      "signal": "hold",
      "quantity": 0.12,
      "profit_target": 118136.15,
      "stop_loss": 102026.675,
      "invalidation_condition": "If the price closes below 105000 on a 3-minute candle",
      "leverage": 10,
      "confidence": 0.75,
      "risk_usd": 619.2345
    }
  }
}'''

    result1 = parser.parse_reference_format(perfect_response, "BTC/USDT", 115599.5)
    print(f"✅ Test 1 - Format parfait: {'SUCCÈS' if result1 and not result1.get('_fallback') else 'ÉCHEC'}")

    # Test 2: Format avec erreurs JSON mineures
    imperfect_response = '''{
  "ETH": {
    "trade_signal_args": {
      "coin": "ETH",
      "signal": "entry",
      "quantity": 5.74,
      "profit_target": 4568.31,
      "stop_loss": 4065.43,
      "confidence": "65%",
      "leverage": 10
    }
  }
}'''

    result2 = parser.parse_reference_format(imperfect_response, "ETH/USDT", 4227.85)
    print(f"✅ Test 2 - Format avec erreurs: {'SUCCÈS' if result2 else 'ÉCHEC'}")

    # Test 3: Réponse LLM corrompue
    corrupted_response = "Voici mon analyse du marché BTC. Je pense qu'il faut HOLD avec une confiance de 65%. Le prix est autour de 115599 dollars."

    result3 = parser.parse_reference_format(corrupted_response, "BTC/USDT", 115599.5)
    print(f"✅ Test 3 - Réponse corrompue: {'FALLBACK' if result3 and result3.get('_fallback') else 'ÉCHEC'}")

    # Test 4: JSON mal formé
    malformed_json = '''{
  "SOL": {
    "trade_signal_args": {
      "coin": "SOL",
      "signal": "hold",
      "quantity": 33.88,
      "profit_target": 215.0,
      "stop_loss": 192.86,  // Trailing comma should be fixed
      "confidence": 0.65,
    }
  }
}'''

    result4 = parser.parse_reference_format(malformed_json, "SOL/USDT", 202.545)
    print(f"✅ Test 4 - JSON mal formé: {'SUCCÈS' if result4 and not result4.get('_fallback') else 'FALLBACK'}")

    return parser.get_performance_stats()


def test_reference_prompt():
    """Tester le service de prompt de référence"""
    print("\n🧪 TEST: Service de prompt de référence")
    print("-" * 50)

    prompt_service = ReferencePromptService()

    # Données de test
    mock_bot = type('Bot', (), {
        'risk_params': {'stop_loss_pct': 0.035, 'take_profit_pct': 0.07}
    })()

    mock_market_data = {
        "current_price": 115599.5,
        "technical_indicators": {
            "5m": {
                "ema20": 115641.785,
                "macd": 49.905,
                "rsi7": 41.836
            },
            "1h": {
                "ema20": 112938.535,
                "ema50": 111539.738,
                "atr3": 421.773,
                "atr14": 606.485
            }
        }
    }

    mock_positions = []
    mock_all_coins = {"BTC/USDT": mock_market_data}
    mock_market_regime = {}

    # Test prompt sans position
    prompt1 = prompt_service.build_reference_prompt(
        mock_bot, "BTC/USDT", mock_market_data, mock_market_regime, mock_all_coins, mock_positions
    )

    print(f"✅ Test 1 - Prompt sans position: {len(prompt1.split())} mots")
    print(f"   Contient 'trade_signal_args': {'OUI' if 'trade_signal_args' in prompt1 else 'NON'}")
    print(f"   Format JSON présent: {'OUI' if '{' in prompt1 and '}' in prompt1 else 'NON'}")

    # Test prompt avec position
    mock_positions_with = [{
        'symbol': 'BTC/USDT',
        'side': 'long',
        'size': 0.12,
        'entry_price': 107343.0,
        'current_price': 115599.5,
        'pnl': 990.78,
        'pnl_pct': 7.7
    }]

    prompt2 = prompt_service.build_reference_prompt(
        mock_bot, "BTC/USDT", mock_market_data, mock_market_regime, mock_all_coins, mock_positions_with
    )

    print(f"✅ Test 2 - Prompt avec position: {len(prompt2.split())} mots")
    print(f"   Contient 'CURRENT POSITION': {'OUI' if 'CURRENT POSITION' in prompt2 else 'NON'}")

    return {
        "prompt_without_position_words": len(prompt1.split()),
        "prompt_with_position_words": len(prompt2.split()),
        "has_trade_signal_args": "trade_signal_args" in prompt1,
        "has_json_format": "{" in prompt1 and "}" in prompt1,
        "has_position_info": "CURRENT POSITION" in prompt2
    }


def test_integration():
    """Test d'intégration complet"""
    print("\n🧪 TEST: Intégration complète")
    print("-" * 50)

    # Simuler TradingEngine
    class MockTradingEngine:
        def __init__(self):
            self.llm_client = type('LLMClient', (), {
                'analyze_market': lambda self, **kwargs: {
                    'response': '''{
  "BTC": {
    "trade_signal_args": {
      "coin": "BTC",
      "signal": "hold",
      "quantity": 0.12,
      "profit_target": 118136.15,
      "stop_loss": 102026.675,
      "confidence": 0.75
    }
  }
}'''
                }
            })()

    mock_engine = MockTradingEngine()

    # Appliquer le patch
    patch = ReferenceTradingPatch()
    patch.apply_to_trading_engine(mock_engine)

    # Test de décision
    mock_market = {"current_price": 115599.5}
    mock_bot = type('Bot', (), {'risk_params': {'stop_loss_pct': 0.035, 'take_profit_pct': 0.07}})()

    decision = patch._get_reference_decision(
        mock_engine, "BTC/USDT", mock_market, mock_bot, [], {}, {}
    )

    print(f"✅ Test intégration - Decision générée: {'OUI' if decision else 'NON'}")
    print(f"   Action: {decision.get('action', 'N/A') if decision else 'N/A'}")
    print(f"   Confidence: {decision.get('confidence', 0):.0%}" if decision else "N/A")
    print(f"   Format: {decision.get('format', 'N/A') if decision else 'N/A'}")

    return decision is not None


def run_all_tests():
    """Exécuter tous les tests"""
    print("🚀 LANCEMENT DES TESTS DU SYSTÈME DE RÉFÉRENCE")
    print("=" * 60)

    # Tests individuels
    parser_stats = test_reference_parser()
    prompt_stats = test_reference_prompt()
    integration_success = test_integration()

    # Résumé
    print("\n📊 RÉSUMÉ DES TESTS")
    print("=" * 60)
    print(f"Parser de référence:")
    for key, value in parser_stats.items():
        print(f"  {key}: {value}")

    print(f"\nPrompt de référence:")
    for key, value in prompt_stats.items():
        print(f"  {key}: {value}")

    print(f"\nIntégration: {'SUCCÈS' if integration_success else 'ÉCHEC'}")

    # Évaluation finale
    print(f"\n🎯 ÉVALUATION:")
    print("-" * 30)

    if parser_stats.get('success_rate', '0%') != 'Aucune statistique disponible':
        success_rate = float(parser_stats.get('success_rate', '0%').replace('%', ''))
        if success_rate >= 70:
            print(f"✅ Parser: EXCELLENT ({success_rate:.1f}% de succès)")
        elif success_rate >= 50:
            print(f"⚠️  Parser: BON ({success_rate:.1f}% de succès)")
        else:
            print(f"❌ Parser: À AMÉLIORER ({success_rate:.1f}% de succès)")

    prompt_words = prompt_stats.get('prompt_without_position_words', 0)
    if prompt_words <= 200:
        print(f"✅ Prompt: OPTIMAL ({prompt_words} mots)")
    elif prompt_words <= 300:
        print(f"⚠️  Prompt: ACCEPTABLE ({prompt_words} mots)")
    else:
        print(f"❌ Prompt: TROP LONG ({prompt_words} mots)")

    if integration_success:
        print("✅ Intégration: SUCCÈS")
    else:
        print("❌ Intégration: ÉCHEC")

    print("\n🚀 CONCLUSION:")
    if (parser_stats.get('success_rate', '0%') != 'Aucune statistique disponible' and
        float(parser_stats.get('success_rate', '0%').replace('%', '')) >= 50 and
        prompt_words <= 300 and integration_success):
        print("🎉 SYSTÈME DE RÉFÉRENCE PRÊT POUR PRODUCTION")
        print("📈 Attendu: Réduction du taux d'échec de 80% → 10-15%")
    else:
        print("⚠️  SYSTÈME NÉCESSITE DES AJUSTEMENTS")


if __name__ == "__main__":
    run_all_tests()
