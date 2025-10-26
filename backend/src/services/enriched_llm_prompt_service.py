"""
Service de génération de prompts LLM enrichis
Inspiré du bot +93% avec contexte complet de session
"""
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

from .trading_memory_service import get_trading_memory
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EnrichedLLMPromptService:
    """
    Service pour générer des prompts enrichis pour Qwen3 Max
    Format similaire au bot +93% : contexte complet de portfolio, performance, positions
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def _format_session_context(self, context: Dict) -> str:
        """Formater le contexte de session"""
        session = context["session"]
        return f"""TRADING SESSION CONTEXT
======================
Session Duration: {session['session_minutes']} minutes
Total Invocations: {session['total_invocations']}
Current Time: {session['current_time']}
"""
    
    def _format_portfolio_context(self, context: Dict) -> str:
        """Formater le contexte portfolio"""
        portfolio = context["portfolio"]
        return f"""PORTFOLIO PERFORMANCE
====================
Initial Capital: ${portfolio['initial_capital']:,.2f}
Current Account Value: ${portfolio['current_equity']:,.2f}
Available Cash: ${portfolio['available_cash']:,.2f} ({portfolio['cash_pct']:.1f}%)
Invested Capital: ${portfolio['invested']:,.2f} ({portfolio['invested_pct']:.1f}%)
Current Total Return: {portfolio['return_pct']:+.2f}% (${portfolio['pnl']:+,.2f})
Sharpe Ratio: {context['sharpe_ratio']:.3f}
"""
    
    def _format_positions_context(self, context: Dict) -> str:
        """Formater les positions actuelles"""
        positions = context["positions"]
        
        if not positions:
            return "CURRENT POSITIONS: None\n"
        
        output = f"CURRENT POSITIONS ({len(positions)})\n{'='*50}\n"
        
        for pos in positions:
            output += f"""
Symbol: {pos['symbol']} | Side: {pos['side']} | Size: {pos['size']:.4f}
Entry Price: ${pos['entry_price']:,.2f} | Current: ${pos['current_price']:,.2f}
PnL: ${pos['pnl']:+,.2f} ({pos['pnl_pct']:+.2f}%)
Stop Loss: ${pos['stop_loss']:,.2f} | Take Profit: ${pos['take_profit']:,.2f}
Notional Value: ${pos['notional_usd']:,.2f}
{'─'*50}"""
        
        return output + "\n"
    
    def _format_trades_today_context(self, context: Dict) -> str:
        """Formater le contexte des trades du jour"""
        trades = context["trades_today"]
        
        output = f"""TRADES TODAY
============
Executed: {trades['trades_today']}/{trades['max_trades_per_day']}
Win Rate (Recent): {trades['win_rate']:.1f}%
Total Closed Trades: {trades['total_closed_trades']}
Winning Trades: {trades['winning_trades']}/{trades['total_closed_trades']}
"""
        
        if trades['best_trade']:
            best = trades['best_trade']
            output += f"Best Trade: {best['symbol']} ${best['pnl']:+,.2f} ({best['pnl_pct']:+.1f}%)\n"
        
        if trades['worst_trade']:
            worst = trades['worst_trade']
            output += f"Worst Trade: {worst['symbol']} ${worst['pnl']:+,.2f} ({worst['pnl_pct']:+.1f}%)\n"
        
        return output + "\n"
    
    def _format_market_data(self, symbol: str, market_snapshot: Dict) -> str:
        """Formater les données de marché (format similaire au bot +93%)"""
        
        # Extract data
        current_price = market_snapshot.get("price", 0)
        technical = market_snapshot.get("technical_indicators", {})
        
        # Multi-timeframe data
        tf_5m = technical.get("5m", {})
        tf_1h = technical.get("1h", {})
        
        output = f"""MARKET DATA FOR {symbol}
{'='*50}

CURRENT STATE
-------------
Price: ${current_price:,.2f}
EMA20 (5m): ${tf_5m.get('ema20', 0):,.2f}
MACD (5m): {tf_5m.get('macd', 0):.3f}
RSI7 (5m): {tf_5m.get('rsi7', 50):.1f}
RSI14 (5m): {tf_5m.get('rsi14', 50):.1f}

INTRADAY SERIES (5-minute intervals, oldest → newest)
---------------------------------------------------
"""
        
        # Series data if available
        if "price_series" in market_snapshot:
            prices = market_snapshot["price_series"][-10:]  # Last 10 points
            output += f"Prices: [{', '.join([f'{p:,.2f}' for p in prices])}]\n"
        
        if "ema_series" in market_snapshot:
            ema = market_snapshot["ema_series"][-10:]
            output += f"EMA20: [{', '.join([f'{e:,.2f}' for e in ema])}]\n"
        
        if "rsi_series" in market_snapshot:
            rsi = market_snapshot["rsi_series"][-10:]
            output += f"RSI7: [{', '.join([f'{r:.1f}' for r in rsi])}]\n"
        
        # Longer-term context
        output += f"""
LONGER-TERM CONTEXT (1-hour timeframe)
-------------------------------------
EMA20: ${tf_1h.get('ema20', 0):,.2f} vs EMA50: ${tf_1h.get('ema50', 0):,.2f}
MACD: {tf_1h.get('macd', 0):.3f}
RSI14: {tf_1h.get('rsi14', 50):.1f}
Volume: {tf_1h.get('volume', 0):,.2f} (Avg: {tf_1h.get('avg_volume', 0):,.2f})
"""
        
        # Trend analysis
        trend_5m = "BULLISH" if tf_5m.get('ema20', 0) > tf_5m.get('ema50', 0) else "BEARISH"
        trend_1h = "BULLISH" if tf_1h.get('ema20', 0) > tf_1h.get('ema50', 0) else "BEARISH"
        
        output += f"""
TREND ANALYSIS
--------------
5-minute: {trend_5m}
1-hour: {trend_1h}
Alignment: {'✓ ALIGNED' if trend_5m == trend_1h else '✗ DIVERGENT'}
"""
        
        return output + "\n"
    
    def _format_multi_coin_market_state(self, market_regime: Dict, all_coins_data: Dict) -> str:
        """Formater l'état global du marché (tous les coins)"""
        
        regime = market_regime.get("regime", "NEUTRAL")
        confidence = market_regime.get("confidence", 0.5)
        breadth = market_regime.get("breadth", {})
        
        output = f"""MULTI-COIN MARKET STATE
{'='*50}
Market Regime: {regime} ({confidence:.0%} confidence)
Breadth: {breadth.get('up', 0)} coins up / {breadth.get('down', 0)} coins down

QUICK SNAPSHOT (All Tradable Assets)
------------------------------------
"""
        
        for symbol, data in all_coins_data.items():
            price = data.get("price", 0)
            rsi = data.get("rsi", 50)
            trend = data.get("trend", "NEUTRAL")
            output += f"{symbol:6} | ${price:>10,.2f} | RSI: {rsi:>5.1f} | {trend}\n"
        
        return output + "\n"
    
    def build_enriched_prompt(
        self,
        bot,
        symbol: str,
        market_snapshot: Dict,
        market_regime: Dict,
        all_coins_data: Dict,
        bot_positions: list = None
    ) -> str:
        """
        Construire le prompt enrichi complet
        Similaire au format du bot +93%
        
        Args:
            bot: Bot instance
            symbol: Trading symbol
            market_snapshot: Market data snapshot
            market_regime: Market regime analysis
            all_coins_data: Multi-coin snapshot
            bot_positions: List of bot positions (to avoid async DB queries)
        """
        
        # Get trading memory context (pass positions to avoid async issues)
        memory = get_trading_memory(self.db, bot.id)
        context = memory.get_full_context(bot, bot_positions)
        
        # Build sections
        session_text = self._format_session_context(context)
        portfolio_text = self._format_portfolio_context(context)
        positions_text = self._format_positions_context(context)
        trades_text = self._format_trades_today_context(context)
        market_state_text = self._format_multi_coin_market_state(market_regime, all_coins_data)
        market_data_text = self._format_market_data(symbol, market_snapshot)
        
        # Build the full prompt
        prompt = f"""You are an expert crypto trader managing a portfolio with Qwen3 Max AI.

{session_text}

{portfolio_text}

{positions_text}

{trades_text}

{market_state_text}

{market_data_text}

YOUR MISSION
============
You are personally responsible for this portfolio's performance.

Current Status:
- Return: {context['portfolio']['return_pct']:+.2f}%
- Cash Available: ${context['portfolio']['available_cash']:,.2f}
- Trades Today: {context['trades_today']['trades_today']}/{context['trades_today']['max_trades_per_day']}
- Active Positions: {len(context['positions'])}

DECISION FRAMEWORK
==================
Be HIGHLY SELECTIVE. Only trade when:
1. Setup is EXCEPTIONAL (not just good)
2. Risk/reward is clearly favorable
3. Aligns with portfolio objectives
4. You have available cash (don't overextend)

Consider:
- "Do I REALLY need to enter this trade right now?"
- "Am I adding value or just overtrading?"
- "What's my exit plan if this goes wrong?"
- "How does this fit my existing positions?"

CONFIDENCE THRESHOLDS
======================
- ENTRY: 75%+ confidence (very high bar)
  → Only if setup is crystal clear
  → Strong trend + good entry point
  → Clear stop loss and profit target

- HOLD: 50-75% confidence
  → Position performing as expected
  → No clear exit signal yet
  → Let winners run

- EXIT: 50%+ confidence
  → Stop loss hit or approaching
  → Profit target reached
  → Setup invalidated

RESPONSE FORMAT
===============
⚠️ CRITICAL: Respond with ONLY a valid JSON object. No explanation text before or after.
Do NOT include markdown code fences (```json). Just pure JSON.

Required format:

{{
  "{symbol}": {{
    "signal": "entry|hold|exit",
    "confidence": 0.75,
    "justification": "Detailed multi-sentence reasoning explaining:
                      1. What you see in the market
                      2. Why this decision makes sense
                      3. Your risk management plan
                      4. How this fits your portfolio",
    "stop_loss": 112000.0,
    "profit_target": 115000.0,
    "invalidation_condition": "Price closes below X on Y timeframe",
    "leverage": 1,
    "risk_usd": 500.0
  }}
}}

CRITICAL REMINDERS
==================
1. You are managing real capital - be conservative
2. Preservation of capital is priority #1
3. Better to miss a trade than force a bad one
4. Quality over quantity - be selective
5. Consider portfolio balance before adding positions

Now analyze {symbol} and respond with ONLY valid JSON (no text, no markdown, no explanation):
"""
        
        return prompt
    
    def parse_llm_response(self, response_text: str, symbol: str) -> Optional[Dict]:
        """
        Parser la réponse JSON du LLM - version robuste
        Gère les cas où le LLM ajoute du texte avant/après le JSON
        """
        try:
            # Remove markdown code fences if present
            cleaned = response_text.strip()
            if cleaned.startswith('```'):
                # Find the actual JSON content between code fences
                lines = cleaned.split('\n')
                json_lines = []
                in_code_block = False
                for line in lines:
                    if line.startswith('```'):
                        in_code_block = not in_code_block
                        continue
                    if in_code_block or (not in_code_block and '{' in line):
                        json_lines.append(line)
                cleaned = '\n'.join(json_lines)
            
            # Try to find JSON in response
            start_idx = cleaned.find('{')
            if start_idx == -1:
                logger.error(f"⚡ ENRICHED | No JSON found in LLM response (len={len(response_text)})")
                logger.debug(f"Response preview: {response_text[:200]}...")
                return None
            
            # Find the matching closing brace
            brace_count = 0
            end_idx = start_idx
            for i in range(start_idx, len(cleaned)):
                if cleaned[i] == '{':
                    brace_count += 1
                elif cleaned[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            if brace_count != 0:
                logger.error("⚡ ENRICHED | Unbalanced braces in JSON")
                return None
            
            json_str = cleaned[start_idx:end_idx]
            data = json.loads(json_str)
            
            logger.info(f"⚡ ENRICHED | Successfully parsed JSON with keys: {list(data.keys())}")
            
            # Extract decision for symbol
            if symbol in data:
                decision = data[symbol]
                
                # Validate required fields
                required = ["signal", "confidence", "justification"]
                missing = [f for f in required if f not in decision]
                if missing:
                    logger.error(f"⚡ ENRICHED | Missing required fields: {missing}")
                    return None
                
                # Normalize signal
                signal = decision["signal"].lower()
                if signal not in ["entry", "hold", "exit"]:
                    logger.error(f"⚡ ENRICHED | Invalid signal: {signal}")
                    return None
                
                logger.info(f"⚡ ENRICHED | Valid decision for {symbol}: {signal.upper()} @ {decision['confidence']:.0%}")
                return decision
            
            logger.error(f"⚡ ENRICHED | Symbol {symbol} not found in response keys: {list(data.keys())}")
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"⚡ ENRICHED | JSON decode error: {e}")
            logger.debug(f"Failed JSON string: {json_str if 'json_str' in locals() else 'N/A'}")
            return None
        except Exception as e:
            logger.error(f"⚡ ENRICHED | Parse error: {e}")
            return None
    
    def get_simple_decision(
        self,
        bot,
        symbol: str,
        market_snapshot: Dict,
        market_regime: Dict,
        all_coins_data: Dict,
        bot_positions: list = None
    ) -> Dict:
        """
        Méthode simplifiée qui retourne une décision formatée
        Compatible avec l'ancienne interface
        
        Args:
            bot: Bot instance
            symbol: Trading symbol
            market_snapshot: Market data snapshot
            market_regime: Market regime analysis
            all_coins_data: Multi-coin snapshot
            bot_positions: List of bot positions (to avoid async DB queries)
        """
        # Build prompt (pass positions)
        prompt = self.build_enriched_prompt(
            bot, symbol, market_snapshot, market_regime, all_coins_data, bot_positions
        )
        
        # Return prompt and metadata
        return {
            "prompt": prompt,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        }

