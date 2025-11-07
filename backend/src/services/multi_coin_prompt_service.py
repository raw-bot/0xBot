"""
Service de prompt corrigé - Analyse TOUS les coins simultanément
Respecte la règle : SOL (position) → HOLD/EXIT, BTC/ETH/BNB/XRP (pas de pos) → ENTRY/HOLD
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MultiCoinPromptService:
    """
    Service de prompt qui analyse TOUS les coins simultanément
    Conform aux exigences utilisateur
    """

    def __init__(self, db=None):
        """Constructeur compatible avec l'interface SimpleLLMPromptService"""
        self.db = db  # Non utilisé mais pour compatibilité

    def get_simple_decision(self, bot, symbol, market_snapshot, market_regime, all_coins_data, bot_positions=None):
        """
        Méthode de compatibilité - wrapper vers get_multi_coin_decision
        Pour être compatible avec l'interface SimpleLLMPromptService
        """
        # ✅ CORRECTION PRÉVENTIVE: Validation all_coins_data
        if all_coins_data is None:
            all_coins_data = {}

        # ✅ CORRECTION PRÉVENTIVE: Vérifier type all_coins_data
        if not isinstance(all_coins_data, dict):
            logger.warning(f"all_coins_data n'est pas un dict (type: {type(all_coins_data)}), conversion en dict vide")
            all_coins_data = {}

        # Utiliser bot_positions si fourni, sinon essayer all_coins_data
        all_positions = bot_positions or []

        prompt_data = self.get_multi_coin_decision(
            bot=bot,
            all_coins_data=all_coins_data,
            all_positions=all_positions
        )

        return {
            "prompt": prompt_data["prompt"],
            "symbol": symbol,
            "timestamp": prompt_data.get("timestamp", "")
        }

    def get_multi_coin_decision(self, bot, all_coins_data, all_positions):
        """
        Génère un prompt multi-coins complet pour analyser TOUS les symboles
        """
        if all_positions is None:
            all_positions = []

        # ✅ CORRECTION PRÉVENTIVE: Gestion robuste des positions
        # all_positions = bot_positions or []  # ERREUR: bot_positions n'existe pas

        # ✅ CORRECTION: Construire position_symbols de manière robuste
        position_symbols = set()
        for pos in all_positions:
            if hasattr(pos, 'symbol'):  # Position object
                position_symbols.add(pos.symbol)
            elif isinstance(pos, dict) and 'symbol' in pos:  # Dict object
                position_symbols.add(pos['symbol'])
            # Sinon ignorer (position malformed)

        # Mapping des symboles vers noms de coins
        coin_mapping = {
            "BTC/USDT": "Bitcoin",
            "ETH/USDT": "Ethereum",
            "SOL/USDT": "Solana",
            "BNB/USDT": "BNB",
            "XRP/USDT": "XRP"
        }

        # Liste des symboles à analyser (dans l'ordre du bot)
        symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]

        # Construction du prompt
        prompt_parts = []
        prompt_parts.append("MULTI-COIN TRADING ANALYSIS")
        prompt_parts.append("=" * 50)
        prompt_parts.append("")

        # État des positions
        if all_positions:
            prompt_parts.append(f"PORTFOLIO STATUS:")
            prompt_parts.append(f"Positions: {len(all_positions)} active")
            for pos in all_positions:
                if hasattr(pos, 'symbol'):  # Position object
                    symbol_name = coin_mapping.get(pos.symbol, pos.symbol)
                    side = pos.side.upper() if hasattr(pos, 'side') else 'UNKNOWN'
                    quantity = float(pos.quantity) if hasattr(pos, 'quantity') else 0
                    position_entry_price = float(pos.position_entry_price) if hasattr(pos, 'position_entry_price') else 0
                    current_market_price = float(pos.current_market_price) if hasattr(pos, 'current_market_price') else 0

                    # Calculate PnL
                    if hasattr(pos, 'side') and pos.side.lower() == "long":
                        pnl = (current_market_price - position_entry_price) * quantity
                    elif hasattr(pos, 'side'):
                        pnl = (position_entry_price - current_market_price) * quantity
                    else:
                        pnl = 0

                    prompt_parts.append(f"  {symbol_name}: {side} {quantity:.4f} @ ${position_entry_price:.2f} (Current: ${current_market_price:.2f})")
                else:  # Dict fallback
                    symbol_name = coin_mapping.get(pos.get('symbol', 'UNKNOWN'), pos.get('symbol', 'UNKNOWN'))
                    side = pos.get('side', 'unknown').upper()
                    size = pos.get('size', 0)
                    position_entry_price = pos.get('position_entry_price', 0)
                    current_market_price = pos.get('current_market_price', 0)
                    pnl = pos.get('pnl', 0)
                    prompt_parts.append(f"  {symbol_name}: {side} {size:.4f} @ ${position_entry_price:.2f} (Current: ${current_market_price:.2f}, PnL: ${pnl:+.2f})")
        else:
            prompt_parts.append("PORTFOLIO STATUS:")
            prompt_parts.append("  No active positions")

        prompt_parts.append("")
        prompt_parts.append("MARKET ANALYSIS:")

        # Analyser chaque symbole
        for symbol in symbols:
            coin_name = coin_mapping.get(symbol, symbol)
            prompt_parts.append("")
            prompt_parts.append(f"🔍 {coin_name} ({symbol})")
            prompt_parts.append("-" * 40)

            # Logique selon présence de position
            if symbol in position_symbols:
                # Coin AVEC position → HOLD vs EXIT
                position = next((p for p in all_positions if (hasattr(p, 'symbol') and p.symbol == symbol) or (isinstance(p, dict) and p.get('symbol') == symbol)), None)
                if position:
                    prompt_parts.append(f"⚠️  HAS POSITION: {coin_name}")
                    # Format position details using object attributes instead of dict access
                    if hasattr(position, 'symbol'):  # Position is an object
                        prompt_parts.append(f"Symbol: {position.symbol} | Side: {position.side.upper()} | Size: {float(position.quantity):.4f}")
                        prompt_parts.append(f"Entry Price: ${float(position.position_entry_price):,.2f} | Current: ${float(position.current_market_price):,.2f}")

                        # Calculate PnL
                        if position.side.lower() == "long":
                            pnl = (Decimal(str(position.current_market_price)) - Decimal(str(position.position_entry_price))) * Decimal(str(position.quantity))
                        else:
                            pnl = (Decimal(str(position.position_entry_price)) - Decimal(str(position.current_market_price))) * Decimal(str(position.quantity))

                        pnl_pct = (pnl / (float(position.position_entry_price) * float(position.quantity))) * 100 if position.quantity > 0 else 0

                        prompt_parts.append(f"PnL: ${pnl:+,.2f} ({pnl_pct:+.2f}%)")
                    else:  # Position is a dict (fallback)
                        prompt_parts.append(f"Symbol: {position.get('symbol', 'N/A')} | Side: {position.get('side', 'long')} | Size: {position.get('size', 0):.4f}")
                        prompt_parts.append(f"Entry Price: ${position.get('position_entry_price', 0):,.2f} | Current: ${position.get('current_market_price', 0):,.2f}")
                        prompt_parts.append(f"PnL: ${position.get('pnl', 0):+,.2f} ({position.get('pnl_pct', 0):+.2f}%)")
                    prompt_parts.append("DECISION: Evaluate HOLD vs EXIT based on invalidation conditions")
                else:
                    prompt_parts.append(f"⚠️  HAS POSITION: {coin_name} (position data not found)")
            else:
                # Coin SANS position → ENTRY vs HOLD
                prompt_parts.append(f"🎯 NO POSITION: {coin_name}")
                prompt_parts.append("DECISION: Look for ENTRY opportunities or HOLD if setup unclear")

            prompt_parts.append("")

        # Instructions finales
        prompt_parts.append("ANALYSIS FRAMEWORK:")
        prompt_parts.append("- Consider market regime, technical indicators, and risk-reward")
        prompt_parts.append("- For coins WITH positions: HOLD (if thesis intact) vs EXIT (if invalidated)")
        prompt_parts.append("- For coins WITHOUT positions: ENTRY (if setup valid) vs HOLD (if unclear)")
        prompt_parts.append("")
        prompt_parts.append("RESPONSE FORMAT:")
        prompt_parts.append("For each coin, provide:")
        prompt_parts.append("1. Signal: HOLD/ENTRY/EXIT")
        prompt_parts.append("2. Confidence: 0.0-1.0")
        prompt_parts.append("3. Reasoning: Brief explanation")
        prompt_parts.append("")
        prompt_parts.append("JSON FORMAT:")
        prompt_parts.append('{"BTC/USDT": {"signal": "HOLD", "confidence": 0.65, "reasoning": "..."}')

        prompt = "\n".join(prompt_parts)

        # Logique pour debug
        logic_type = "0 positions → HOLD/EXIT, 5 new → ENTRY/HOLD" if not all_positions else "Has positions → HOLD/EXIT"

        return {
            "prompt": prompt,
            "timestamp": datetime.utcnow().isoformat(),
            "logic": logic_type,
            "symbols_count": len(symbols),
            "positions_count": len(all_positions)
        }

    def parse_multi_coin_response(self, response_text, target_symbols=None):
        """
        Parse la réponse LLM multi-coins au format JSON
        """
        if target_symbols is None:
            target_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]

        try:
            # Essayer de parser comme JSON direct
            if response_text.strip().startswith('{'):
                data = json.loads(response_text)
                return data

            # Sinon, essayer d'extraire le JSON
            start_brace = response_text.find('{')
            end_brace = response_text.rfind('}')

            if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
                json_part = response_text[start_brace:end_brace+1]
                data = json.loads(json_part)
                return data
            else:
                logger.error(f"Could not find JSON in response: {response_text[:100]}...")
                return {}

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse multi-coin JSON response: {e}")
            logger.error(f"Response text: {response_text[:200]}...")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error parsing multi-coin response: {e}")
            return {}

    def get_decision_for_symbol(self, symbol, response_text):
        """
        Extraire la décision pour un symbole spécifique de la réponse LLM
        """
        if not response_text.strip():
            return {
                "action": "hold",
                "confidence": 0.6,
                "reasoning": f"Réponse LLM vide pour {symbol}, default HOLD"
            }

        try:
            # Extraire uniquement la décision pour le symbol demandé
            decisions = self.parse_multi_coin_response(response_text, [symbol])

            # ✅ CORRECTION PRÉVENTIVE: Vérifier si symbol trouvé
            if symbol in decisions:
                decision = decisions[symbol]
                return {
                    "action": decision.get("signal", "hold"),
                    "confidence": decision.get("confidence", 0.6),
                    "reasoning": decision.get("reasoning", f"Décision pour {symbol}")
                }
            else:
                # ✅ CORRECTION PRÉVENTIVE: Fallback si symbol non trouvé
                return {
                    "action": "hold",
                    "confidence": 0.6,
                    "reasoning": f"Symbol {symbol} non trouvé dans réponse LLM, default HOLD"
                }
        except Exception as e:
            # ✅ CORRECTION PRÉVENTIVE: Fallback en cas d'erreur de parsing
            logger.warning(f"Erreur parsing {symbol}: {e}, fallback HOLD")
            return {
                "action": "hold",
                "confidence": 0.6,
                "reasoning": f"Erreur parsing pour {symbol}, default HOLD"
            }

    def parse_simple_response(self, response_text, symbol, current_market_price=0):
        """
        Méthode de compatibilité pour parser les réponses LLM
        Compatible avec l'interface SimpleLLMPromptService
        """
        return self.get_decision_for_symbol(symbol, response_text)
