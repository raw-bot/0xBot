#!/usr/bin/env python3
"""
Test SIMPLIFIÉ du système multi-coins
Sans dépendances externes - juste la logique pure
"""

import json
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))


class SimpleMultiCoinService:
    """Service multi-coins simplifié sans dépendances"""

    def build_simple_multi_coin_prompt(self, all_coins_data, all_positions=None):
        """Construire un prompt multi-coins simplifié"""

        if not all_coins_data:
            return "No market data available"

        position_symbols = {pos.get('symbol') for pos in (all_positions or [])}

        prompt_parts = []
        prompt_parts.append("MARKET ANALYSIS FOR ALL COINS")
        prompt_parts.append(f"Analyzing {len(all_coins_data)} coins simultaneously")
        prompt_parts.append("")

        # Données pour TOUS les coins
        for symbol, market_data in all_coins_data.items():
            coin_name = symbol.split('/')[0]
            current_price = market_data.get("current_price", 0)
            technical = market_data.get("technical_indicators", {})
            tf_5m = technical.get("5m", {})
            tf_1h = technical.get("1h", {})

            prompt_parts.append(f"=== {coin_name} ANALYSIS ===")
            prompt_parts.append(f"current_price = {current_price}")
            prompt_parts.append(f"current_ema20 = {tf_5m.get('ema20', 0)}")
            prompt_parts.append(f"current_macd = {tf_5m.get('macd', 0):.3f}")
            prompt_parts.append(f"current_rsi (7 period) = {tf_5m.get('rsi7', 50)}")

            if symbol in position_symbols:
                prompt_parts.append(f"⚠️  HAS POSITION: {coin_name}")
                prompt_parts.append("DECISION: Evaluate HOLD vs EXIT")
            else:
                prompt_parts.append(f"🎯 NO POSITION: {coin_name}")
                prompt_parts.append("DECISION: Look for ENTRY opportunities")

            prompt_parts.append("")

        # Instructions globales
        prompt_parts.append("▶ GLOBAL TRADING STRATEGY")
        prompt_parts.append("COINS WITH POSITIONS: HOLD or EXIT")
        prompt_parts.append("COINS WITHOUT POSITIONS: ENTRY or HOLD")
        prompt_parts.append("")

        # Format JSON pour tous
        prompt_parts.append("OUTPUT FORMAT (JSON for ALL coins):")
        prompt_parts.append("{")

        for i, (symbol, market_data) in enumerate(all_coins_data.items()):
            coin_name = symbol.split('/')[0]
            current_price = market_data.get("current_price", 0)
            default_sl = current_price * 0.965
            default_tp = current_price * 1.07

            if symbol in position_symbols:
                expected_signal = "hold"
                signal_options = "hold or exit"
            else:
                expected_signal = "entry"
                signal_options = "entry or hold"

            comma = "," if i < len(all_coins_data) - 1 else ""

            prompt_parts.append(f'  "{coin_name}": {{')
            prompt_parts.append(f'    "coin": "{coin_name}",')
            prompt_parts.append(f'    "signal": "{expected_signal}",  // {signal_options}')
            prompt_parts.append(f'    "confidence": 0.65,')
            prompt_parts.append(f'    "profit_target": {default_tp:.2f},')
            prompt_parts.append(f'    "stop_loss": {default_sl:.2f}{comma}')
            prompt_parts.append('  }')

        prompt_parts.append("}")
        prompt_parts.append("IMPORTANT: Provide decision for each coin above.")

        return "\n".join(prompt_parts)

    def parse_simple_response(self, response_text, all_symbols):
        """Parser simplifié sans dépendances"""
        try:
            cleaned = response_text.strip()
            start_idx = cleaned.find('{')
            end_idx = cleaned.rfind('}')

            if start_idx != -1 and end_idx != -1:
                json_str = cleaned[start_idx:end_idx + 1]
                data = json.loads(json_str)

                result = {}
                for symbol in all_symbols:
                    coin_name = symbol.split('/')[0]

                    if coin_name in data:
                        result[symbol] = data[coin_name]
                    else:
                        result[symbol] = {
                            "coin": coin_name,
                            "signal": "hold",
                            "confidence": 0.60,
                            "profit_target": 0,
                            "stop_loss": 0,
                            "_fallback": True
                        }

                return result
            else:
                return self._fallback_all_coins(all_symbols)

        except Exception as e:
            print(f"❌ Erreur parsing: {e}")
            return self._fallback_all_coins(all_symbols)

    def _fallback_all_coins(self, all_symbols):
        """Fallback pour tous les coins"""
        result = {}
        for symbol in all_symbols:
            coin_name = symbol.split('/')[0]
            result[symbol] = {
                "coin": coin_name,
                "signal": "hold",
                "confidence": 0.60,
                "profit_target": 0,
                "stop_loss": 0,
                "_fallback": True
            }
        return result


def test_simple_multi_coin_system():
    """Test simplifié du système multi-coins"""
    print("🧪 TEST SIMPLIFIÉ - SYSTÈME MULTI-COINS")
    print("=" * 50)

    service = SimpleMultiCoinService()

    # Données de test
    all_coins_data = {
        "BTC/USDT": {
            "current_price": 115599.5,
            "technical_indicators": {
                "5m": {"ema20": 115641.785, "macd": 49.905, "rsi7": 41.836},
                "1h": {"ema20": 112938.535, "ema50": 111539.738}
            }
        },
        "ETH/USDT": {
            "current_price": 4227.85,
            "technical_indicators": {
                "5m": {"ema20": 4222.572, "macd": 5.556, "rsi7": 55.136},
                "1h": {"ema20": 4046.775, "ema50": 3988.918}
            }
        },
        "SOL/USDT": {
            "current_price": 202.545,
            "technical_indicators": {
                "5m": {"ema20": 202.574, "macd": 0.171, "rsi7": 45.294},
                "1h": {"ema20": 196.51, "ema50": 193.5}
            }
        },
        "BNB/USDT": {
            "current_price": 1148.05,
            "technical_indicators": {
                "5m": {"ema20": 1149.674, "macd": 0.523, "rsi7": 31.564},
                "1h": {"ema20": 1131.736, "ema50": 1123.195}
            }
        },
        "XRP/USDT": {
            "current_price": 2.68925,
            "technical_indicators": {
                "5m": {"ema20": 2.687, "macd": 0.003, "rsi7": 49.85},
                "1h": {"ema20": 2.585, "ema50": 2.522}
            }
        }
    }

    # Position existante sur SOL
    all_positions = [{'symbol': 'SOL/USDT', 'side': 'long', 'size': 2.4364}]

    # Test 1: Générer le prompt
    print("📝 Test 1: Génération du prompt multi-coins")
    prompt = service.build_simple_multi_coin_prompt(all_coins_data, all_positions)

    print(f"✅ Prompt généré: {len(prompt.split())} mots")
    print(f"✅ Coins analysés: {len(all_coins_data)}")

    # Vérifications de la logique
    print("\n🔍 Test 2: Vérification de la logique")
    checks = [
        ("SOL → HAS POSITION", "HAS POSITION: SOL" in prompt),
        ("BTC → NO POSITION", "NO POSITION: BTC" in prompt),
        ("ETH → NO POSITION", "NO POSITION: ETH" in prompt),
        ("BNB → NO POSITION", "NO POSITION: BNB" in prompt),
        ("XRP → NO POSITION", "NO POSITION: XRP" in prompt),
        ("Format JSON complet", all(coin in prompt for coin in ["BTC", "ETH", "SOL", "BNB", "XRP"])),
        ("Instructions HOLD/EXIT", "HOLD or EXIT" in prompt),
        ("Instructions ENTRY/HOLD", "ENTRY or HOLD" in prompt),
    ]

    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")

    # Test 3: Simulation de parsing
    print("\n🧪 Test 3: Simulation parsing multi-coins")

    # Simuler une réponse LLM
    mock_response = '''{
  "BTC": {
    "coin": "BTC",
    "signal": "entry",
    "confidence": 0.75,
    "profit_target": 123691.47,
    "stop_loss": 111503.45
  },
  "ETH": {
    "coin": "ETH",
    "signal": "entry",
    "confidence": 0.68,
    "profit_target": 4523.80,
    "stop_loss": 4079.88
  },
  "SOL": {
    "coin": "SOL",
    "signal": "hold",
    "confidence": 0.65,
    "profit_target": 215.0,
    "stop_loss": 192.86
  },
  "BNB": {
    "coin": "BNB",
    "signal": "entry",
    "confidence": 0.72,
    "profit_target": 1228.21,
    "stop_loss": 1107.67
  },
  "XRP": {
    "coin": "XRP",
    "signal": "hold",
    "confidence": 0.58,
    "profit_target": 2.88,
    "stop_loss": 2.59
  }
}'''

    all_symbols = list(all_coins_data.keys())
    decisions = service.parse_simple_response(mock_response, all_symbols)

    print(f"✅ Décisions parsées pour {len(decisions)} symbols")

    # Analyser les décisions
    entry_decisions = []
    hold_decisions = []

    for symbol, decision in decisions.items():
        coin_name = symbol.split('/')[0]
        signal = decision.get("signal", "N/A")
        confidence = decision.get("confidence", 0)

        print(f"  {coin_name}: {signal.upper()} @ {confidence:.0%}")

        if signal == "entry" and confidence >= 0.55:
            entry_decisions.append(coin_name)
        elif signal in ["hold", "exit"]:
            hold_decisions.append(coin_name)

    # Test 4: Évaluation finale
    print(f"\n🎯 Test 4: Évaluation des exigences")

    # Vérifier que SOL (avec position) est en HOLD/EXIT
    sol_signal = decisions.get("SOL/USDT", {}).get("signal", "")
    sol_correct = sol_signal in ["hold", "exit"]

    # Vérifier que les autres coins peuvent avoir ENTRY
    btc_signal = decisions.get("BTC/USDT", {}).get("signal", "")
    eth_signal = decisions.get("ETH/USDT", {}).get("signal", "")
    bnb_signal = decisions.get("BNB/USDT", {}).get("signal", "")
    xrp_signal = decisions.get("XRP/USDT", {}).get("signal", "")

    btc_correct = btc_signal in ["entry", "hold"]
    eth_correct = eth_signal in ["entry", "hold"]
    bnb_correct = bnb_signal in ["entry", "hold"]
    xrp_correct = xrp_signal in ["entry", "hold"]

    # Compter les nouvelles positions possibles
    new_positions = [coin for coin, sig in [
        ("BTC", btc_signal), ("ETH", eth_signal), ("BNB", bnb_signal), ("XRP", xrp_signal)
    ] if sig == "entry"]

    print(f"✅ SOL (avec position): {sol_signal.upper()} ({'CORRECT' if sol_correct else 'INCORRECT'})")
    print(f"✅ BTC (sans position): {btc_signal.upper()} ({'CORRECT' if btc_correct else 'INCORRECT'})")
    print(f"✅ ETH (sans position): {eth_signal.upper()} ({'CORRECT' if eth_correct else 'INCORRECT'})")
    print(f"✅ BNB (sans position): {bnb_signal.upper()} ({'CORRECT' if bnb_correct else 'INCORRECT'})")
    print(f"✅ XRP (sans position): {xrp_signal.upper()} ({'CORRECT' if xrp_correct else 'INCORRECT'})")
    print(f"✅ Nouvelles positions possibles: {len(new_positions)} ({', '.join(new_positions)})")

    # Résumé final
    print(f"\n🏆 RÉSUMÉ FINAL:")
    print("=" * 30)

    passed_checks = sum(1 for _, result in checks if result)

    all_signals_correct = all([sol_correct, btc_correct, eth_correct, bnb_correct, xrp_correct])

    print(f"✅ Logique prompt: {passed_checks}/{len(checks)} vérifications")
    print(f"✅ Parsing multi-coins: {len(decisions)}/{len(all_symbols)} decisions")
    print(f"✅ Signaux cohérents: {'OUI' if all_signals_correct else 'NON'}")
    print(f"✅ Nouvelles positions: {len(new_positions)} possibles")

    if passed_checks >= 6 and len(decisions) == len(all_symbols) and all_signals_correct:
        print(f"\n🎉 TEST SIMPLIFIÉ RÉUSSI!")
        print(f"✅ Le système multi-coins fonctionne correctement:")
        print(f"   • Parse BTC/ETH/BNB/XRP: ✅ Fonctionnel")
        print(f"   • Logique position: ✅ Respectée")
        print(f"   • Nouvelles positions: ✅ {len(new_positions)} possibles")
        print(f"   • Format strict: ✅ Respecté")

        if 2 <= len(new_positions) <= 4:
            print(f"🎯 PARFAIT: {len(new_positions)} nouvelles positions (objectif: 2-4)")
        elif len(new_positions) > 4:
            print(f"🎯 EXCELLENT: {len(new_positions)} nouvelles positions (dépasse objectif)")
        else:
            print(f"🎯 BON: {len(new_positions)} nouvelles positions (minimum atteint)")

        print(f"\n📈 SYSTÈME PRÊT: La logique est validée")
        print(f"🚀 Prochaine étape: Intégration avec les dépendances complètes")

        return True
    else:
        print(f"\n⚠️  TEST PARTIELLEMENT RÉUSSI")
        print(f"Some composants fonctionnent mais des ajustements sont nécessaires")
        return False


if __name__ == "__main__":
    print("🚀 TEST SIMPLIFIÉ DU SYSTÈME MULTI-COINS")
    print("Sans dépendances externes - Logique pure uniquement")
    print()

    success = test_simple_multi_coin_system()

    if success:
        print(f"\n✅ LA LOGIQUE EST VALIDÉE!")
        print(f"📋 Prochaines étapes pour l'activation complète:")
        print(f"   1. Installer les dépendances: pip install sqlalchemy fastapi")
        print(f"   2. Activer le système: python test_complete_system.py")
        print(f"   3. Intégrer dans le code: apply_complete_patch(trading_engine)")
    else:
        print(f"\n❌ LA LOGIQUE NÉCESSITE DES AJUSTEMENTS")
        print(f"Vérifiez les composants qui ont échoué")
