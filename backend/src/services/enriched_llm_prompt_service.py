"""
Service de génération de prompts LLM enrichis
Inspiré du bot +93% avec contexte complet de session
"""
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal

from .trading_memory_service import get_trading_memory
from sqlalchemy.orm import Session

# Import du logger dédié aux décisions LLM
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from llm_decision_logger import get_llm_decision_logger
    LLM_LOGGER_ENABLED = True
except ImportError:
    LLM_LOGGER_ENABLED = False
    print("⚠️ LLM Decision Logger not found - detailed logging disabled")

logger = logging.getLogger(__name__)

# ANSI color codes for terminal output (same as trading_engine_service.py)
CYAN = '\033[96m'    # Bright cyan
RESET = '\033[0m'    # Reset color


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
        """Formater les données de marché (format EXACT du bot +93%)"""
        
        # Extract data - use current_price consistently
        current_price = market_snapshot.get("current_price", market_snapshot.get("price", 0))
        technical = market_snapshot.get("technical_indicators", {})
        
        # Multi-timeframe data
        tf_5m = technical.get("5m", {})
        tf_1h = technical.get("1h", {})
        
        # Open Interest and Funding Rate (from market_snapshot)
        open_interest = market_snapshot.get("open_interest", {})
        oi_latest = open_interest.get("latest", 0)
        oi_average = open_interest.get("average", 0)
        funding_rate = market_snapshot.get("funding_rate", 0)
        
        # Get values with validation - detect if we have real data or defaults
        ema20_val = tf_5m.get('ema20', 0)
        macd_val = tf_5m.get('macd', 0)
        rsi7_val = tf_5m.get('rsi7')
        rsi14_val = tf_5m.get('rsi14')
        
        # Build indicator string with validation warnings
        if rsi7_val is None or rsi7_val == 50:
            rsi7_str = "N/A (need more data)"
        else:
            rsi7_str = f"{rsi7_val:.3f}"
        
        if rsi14_val is None or rsi14_val == 50:
            rsi14_str = "N/A (need more data)"
        else:
            rsi14_str = f"{rsi14_val:.3f}"
        
        output = f"""ALL {symbol} DATA
current_price = {current_price}, current_ema20 = {ema20_val}, current_macd = {macd_val:.3f}, current_rsi (7 period) = {rsi7_str}, current_rsi (14 period) = {rsi14_str}
In addition, here is the latest {symbol} open interest and funding rate for perps (the instrument you are trading):
Open Interest: Latest: {oi_latest:.2f} Average: {oi_average:.2f}
Funding Rate: {funding_rate}

Intraday series (5‑minute intervals, oldest → latest):
"""
        
        # Series data if available (last 10 points)
        if "price_series" in market_snapshot:
            prices = market_snapshot["price_series"][-10:]
            output += f"Mid prices: [{', '.join([str(p) for p in prices])}]\n"
        
        if "ema20_series" in market_snapshot:
            ema = market_snapshot["ema20_series"][-10:]
            output += f"EMA indicators (20‑period): [{', '.join([str(e) for e in ema])}]\n"
        
        if "macd_series" in market_snapshot:
            macd = market_snapshot["macd_series"][-10:]
            output += f"MACD indicators: [{', '.join([str(m) for m in macd])}]\n"
        
        if "rsi7_series" in market_snapshot:
            rsi7 = market_snapshot["rsi7_series"][-10:]
            output += f"RSI indicators (7‑Period): [{', '.join([f'{r:.3f}' for r in rsi7])}]\n"
        
        if "rsi14_series" in market_snapshot:
            rsi14 = market_snapshot["rsi14_series"][-10:]
            output += f"RSI indicators (14‑Period): [{', '.join([f'{r:.3f}' for r in rsi14])}]\n"
        
        # Longer-term context (4-hour timeframe)
        output += f"""Longer‑term context (4‑hour timeframe):
20‑Period EMA: {tf_1h.get('ema20', 0)} vs. 50‑Period EMA: {tf_1h.get('ema50', 0)}
3‑Period ATR: {tf_1h.get('atr3', 0)} vs. 14‑Period ATR: {tf_1h.get('atr14', 0)}
Current Volume: {tf_1h.get('volume', 0)} vs. Average Volume: {tf_1h.get('avg_volume', 0)}
"""
        
        # MACD and RSI series for 4h if available
        if "macd_series_4h" in market_snapshot:
            macd_4h = market_snapshot["macd_series_4h"][-10:]
            output += f"MACD indicators: [{', '.join([str(m) for m in macd_4h])}]\n"
        
        if "rsi14_series_4h" in market_snapshot:
            rsi14_4h = market_snapshot["rsi14_series_4h"][-10:]
            output += f"RSI indicators (14‑Period): [{', '.join([f'{r:.3f}' for r in rsi14_4h])}]\n"
        
        return output
    
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
        Format EXACT du bot +93% - affiche TOUS les coins en détail
        
        Args:
            bot: Bot instance
            symbol: Trading symbol (principal)
            market_snapshot: Market data snapshot
            market_regime: Market regime analysis
            all_coins_data: Multi-coin snapshot (DICT avec toutes les données de chaque coin)
            bot_positions: List of bot positions (to avoid async DB queries)
        """
        
        # Get trading memory context (pass positions to avoid async issues)
        memory = get_trading_memory(self.db, bot.id)
        context = memory.get_full_context(bot, bot_positions)
        
        # Get current price for example calculations - consistent order: current_price first
        current_price = market_snapshot.get("current_price", market_snapshot.get("price", 0))
        
        # Get SL/TP percentages from bot's risk_params
        stop_loss_pct = bot.risk_params.get("stop_loss_pct", 0.035)  # 3.5% default
        take_profit_pct = bot.risk_params.get("take_profit_pct", 0.07)  # 7% default
        
        # Calculate example prices using Decimal to avoid type errors
        if current_price > 0:
            example_sl = float(Decimal(str(current_price)) * (Decimal("1") - Decimal(str(stop_loss_pct))))
            example_tp = float(Decimal(str(current_price)) * (Decimal("1") + Decimal(str(take_profit_pct))))
        else:
            example_sl = 112000.0
            example_tp = 115000.0
        
        # Build sections
        session_text = self._format_session_context(context)
        portfolio_text = self._format_portfolio_context(context)
        positions_text = self._format_positions_context(context)
        trades_text = self._format_trades_today_context(context)
        
        # Format ALL COINS DATA (comme le bot +93%)
        all_coins_market_data = "CURRENT MARKET STATE FOR ALL COINS\n"
        all_coins_market_data += "="*50 + "\n\n"
        
        # Afficher TOUS les coins en détail
        for coin_symbol, coin_data in all_coins_data.items():
            all_coins_market_data += self._format_market_data(coin_symbol, coin_data)
            all_coins_market_data += "\n"
        
        # Build the full prompt - Format EXACT du bot +93%
        prompt = f"""It has been {context['session']['session_minutes']} minutes since you started trading. The current time is {context['session']['current_time']} and you've been invoked {context['session']['total_invocations']} times. Below, we are providing you with a variety of state data, price data, and predictive signals so you can discover alpha. Below that is your current account information, value, performance, positions, etc. ALL OF THE PRICE OR SIGNAL DATA BELOW IS ORDERED: OLDEST → NEWEST Timeframes note: Unless stated otherwise in a section title, intraday series are provided at 3‑minute intervals. If a coin uses a different interval, it is explicitly stated in that coin's section.

{all_coins_market_data}

HERE IS YOUR ACCOUNT INFORMATION & PERFORMANCE
Current Total Return (percent): {context['portfolio']['return_pct']:.2f}%
Available Cash: {context['portfolio']['available_cash']:.2f}
Current Account Value: {context['portfolio']['current_equity']:.2f}

{positions_text}

Sharpe Ratio: {context['sharpe_ratio']:.3f}

▶ CHAIN_OF_THOUGHT
First, analyze EACH coin's current state:
- Check existing positions for invalidation conditions
- Review technical indicators for entry opportunities
- Consider portfolio balance and risk management

For each coin:
1. Review the position (if exists) - check if invalidation condition is met
2. Analyze technical indicators for new opportunities
3. Make HOLD/ENTRY/EXIT decision based on:
   - Invalidation conditions (non-negotiable)
   - Technical alignment (RSI, MACD, EMA, trend)
   - Risk/reward ratio
   - Portfolio balance

⚠️ IMPORTANT: If you see "N/A (need more data)" for any indicator, it means insufficient historical data.
In this case, you MUST use "hold" signal with confidence below 0.55 (55%) and explain that more data is needed.
DO NOT make trading decisions based on incomplete or default indicator values.

CONFIDENCE LEVELS:
- 75-85%: Very strong (all indicators aligned with real data)
- 65-75%: Strong (most indicators aligned with real data)
- 55-65%: Decent (mixed but positive bias with real data)
- Below 55%: Insufficient data, use "hold" to wait for more candles

▶ CRITICAL: YOU MUST OUTPUT JSON
After your analysis, you MUST output a JSON object. No exceptions.
The JSON MUST be valid and parseable. Do not add any text after the JSON.

JSON FORMAT (THIS IS MANDATORY):
{{
  "{symbol}": {{
    "signal": "hold" or "entry" or "exit",
    "confidence": 0.65,
    "justification": "Brief reason for decision",
    "entry_price": {current_price:.2f},
    "stop_loss": {example_sl:.2f},
    "profit_target": {example_tp:.2f},
    "side": "long",
    "size_pct": 0.05
  }}
}}

RULES:
- signal: Must be "hold", "entry", or "exit" (lowercase)
- confidence: Float between 0 and 1 (e.g., 0.65 for 65%)
- entry_price: Current market price ${current_price:.2f}
- stop_loss: Price below entry (example: ${example_sl:.2f} is {stop_loss_pct*100:.1f}% below)
- profit_target: Price above entry (example: ${example_tp:.2f} is {take_profit_pct*100:.1f}% above)
- side: Always "long" for now
- size_pct: Position size as decimal (0.05 = 5% of capital)

Now analyze {symbol} and output ONLY the JSON object.
"""
        
        return prompt
    
    def _parse_text_decision(self, response_text: str, symbol: str, current_price: float = 0) -> Optional[Dict]:
        """
        Fallback parser for text-only responses (when LLM doesn't output JSON).
        Looks for keywords like HOLD, ENTRY, EXIT in the text.
        """
        import re
        from decimal import Decimal
        
        text_lower = response_text.lower()
        
        # Try to find decision keyword
        signal = "hold"  # default
        if "entry" in text_lower or "buy" in text_lower:
            signal = "entry"
        elif "exit" in text_lower or "sell" in text_lower or "close" in text_lower:
            signal = "exit"
        
        # Try to extract confidence
        confidence = 0.5
        conf_match = re.search(r'confidence[:\s]+(\d+)%', text_lower)
        if conf_match:
            confidence = float(conf_match.group(1)) / 100.0
        
        # Build fallback decision - use Decimal for price calculations
        decision = {
            "signal": signal,
            "confidence": confidence,
            "justification": f"Parsed from text response: {response_text[:100]}...",
            "entry_price": float(current_price) if current_price else 0,
            "stop_loss": float(Decimal(str(current_price)) * Decimal("0.965")) if current_price else 0,  # 3.5% below
            "profit_target": float(Decimal(str(current_price)) * Decimal("1.07")) if current_price else 0,  # 7% above
            "side": "long",
            "size_pct": 0.05
        }
        
        logger.info(f"⚡ ENRICHED | Fallback text parser extracted: {signal.upper()} @ {confidence:.0%}")
        return decision
    
    def parse_llm_response(
        self,
        response_text: str,
        symbol: str,
        original_prompt: Optional[str] = None,
        current_price: float = 0
    ) -> Optional[Dict]:
        """
        Parser la réponse JSON du LLM - version robuste avec fallback text parser.
        Gère les cas où le LLM ajoute du texte avant/après le JSON.
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
                logger.warning(f"⚡ ENRICHED | No JSON found in LLM response (len={len(response_text)})")
                logger.info(f"⚡ ENRICHED | Attempting fallback text parser...")
                
                # Try fallback text parser
                fallback_decision = self._parse_text_decision(response_text, symbol, current_price)
                if fallback_decision:
                    # Log with detailed info
                    if LLM_LOGGER_ENABLED and original_prompt:
                        llm_logger = get_llm_decision_logger()
                        llm_logger.log_error(
                            symbol=symbol,
                            prompt=original_prompt,
                            error_message="No JSON found - used fallback text parser",
                            llm_response=response_text
                        )
                    return fallback_decision
                
                # If fallback also fails
                if LLM_LOGGER_ENABLED and original_prompt:
                    llm_logger = get_llm_decision_logger()
                    llm_logger.log_error(
                        symbol=symbol,
                        prompt=original_prompt,
                        error_message="No JSON found and fallback parser failed",
                        llm_response=response_text
                    )
                
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
                
                # Log error with detailed info
                if LLM_LOGGER_ENABLED and original_prompt:
                    llm_logger = get_llm_decision_logger()
                    llm_logger.log_error(
                        symbol=symbol,
                        prompt=original_prompt,
                        error_message="Unbalanced braces in JSON",
                        llm_response=response_text
                    )
                
                return None
            
            json_str = cleaned[start_idx:end_idx]
            data = json.loads(json_str)
            
            logger.info(f"⚡ ENRICHED | Successfully parsed JSON with keys: {list(data.keys())}")
            
            # Extract decision for symbol
            if symbol in data:
                decision = data[symbol]
                
                # Validate required fields for entry signals
                required = ["signal", "confidence", "justification"]
                missing = [f for f in required if f not in decision]
                if missing:
                    logger.error(f"⚡ ENRICHED | Missing required fields: {missing}")
                    
                    # Log error with detailed info
                    if LLM_LOGGER_ENABLED and original_prompt:
                        llm_logger = get_llm_decision_logger()
                        llm_logger.log_error(
                            symbol=symbol,
                            prompt=original_prompt,
                            error_message=f"Missing required fields: {missing}",
                            llm_response=response_text
                        )
                    
                    return None

                # For entry signals, validate additional required fields
                if decision["signal"].lower() == "entry":
                    entry_required = ["entry_price", "side", "stop_loss", "profit_target"]
                    entry_missing = [f for f in entry_required if f not in decision]
                    if entry_missing:
                        logger.error(f"⚡ ENRICHED | Missing entry fields: {entry_missing}")
                        
                        # Log error with detailed info
                        if LLM_LOGGER_ENABLED and original_prompt:
                            llm_logger = get_llm_decision_logger()
                            llm_logger.log_error(
                                symbol=symbol,
                                prompt=original_prompt,
                                error_message=f"Missing entry fields: {entry_missing}",
                                llm_response=response_text
                            )
                        
                        return None
                
                # Normalize signal
                signal = decision["signal"].lower()
                if signal not in ["entry", "hold", "exit"]:
                    logger.error(f"⚡ ENRICHED | Invalid signal: {signal}")
                    
                    # Log error with detailed info
                    if LLM_LOGGER_ENABLED and original_prompt:
                        llm_logger = get_llm_decision_logger()
                        llm_logger.log_error(
                            symbol=symbol,
                            prompt=original_prompt,
                            error_message=f"Invalid signal: {signal}",
                            llm_response=response_text
                        )
                    
                    return None
                
                logger.info(f"⚡ ENRICHED | Valid decision for {symbol}: {signal.upper()} @ {decision['confidence']:.0%}")
                
                # ========== LOGGING DÉTAILLÉ ==========
                # Log the complete decision to dedicated files
                if LLM_LOGGER_ENABLED and original_prompt:
                    llm_logger = get_llm_decision_logger()
                    
                    # Prepare metadata
                    metadata = {
                        "confidence": decision.get('confidence'),
                        "signal": signal,
                        "entry_price": decision.get('entry_price'),
                        "stop_loss": decision.get('stop_loss'),
                        "profit_target": decision.get('profit_target'),
                        "size_pct": decision.get('size_pct')
                    }
                    
                    llm_logger.log_decision(
                        symbol=symbol,
                        prompt=original_prompt,
                        llm_raw_response=response_text,
                        parsed_decision=decision,
                        final_action=signal.upper(),
                        metadata=metadata
                    )
                    
                    logger.info(f"📝 Decision logged to: logs/llm_decisions/")
                # ========== FIN LOGGING ==========
                
                return decision
            
            logger.error(f"⚡ ENRICHED | Symbol {symbol} not found in response keys: {list(data.keys())}")
            
            # Log error with detailed info
            if LLM_LOGGER_ENABLED and original_prompt:
                llm_logger = get_llm_decision_logger()
                llm_logger.log_error(
                    symbol=symbol,
                    prompt=original_prompt,
                    error_message=f"Symbol {symbol} not found in response keys: {list(data.keys())}",
                    llm_response=response_text
                )
            
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"⚡ ENRICHED | JSON decode error: {e}")
            logger.debug(f"Failed JSON string: {json_str if 'json_str' in locals() else 'N/A'}")
            
            # Log error with detailed info
            if LLM_LOGGER_ENABLED and original_prompt:
                llm_logger = get_llm_decision_logger()
                llm_logger.log_error(
                    symbol=symbol,
                    prompt=original_prompt,
                    error_message=f"JSON decode error: {e}",
                    llm_response=response_text
                )
            
            return None
        except Exception as e:
            logger.error(f"⚡ ENRICHED | Parse error: {e}")

            # Log error with detailed info
            if LLM_LOGGER_ENABLED and original_prompt:
                llm_logger = get_llm_decision_logger()
                llm_logger.log_error(
                    symbol=symbol,
                    prompt=original_prompt,
                    error_message=f"Parse error: {e}",
                    llm_response=response_text
                )

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