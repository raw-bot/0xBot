"""
Enhanced Multi-Coin Prompt Service - NoF1-Style Trading Intelligence

Generates comprehensive prompts with:
1. RAW DATA DASHBOARD (Price Structure, Funding, OI, Volume)
2. NARRATIVE VS REALITY CHECK (News classification)
3. PAIN TRADE ANALYSIS (Squeeze detection, Trigger levels)
4. ALPHA SETUPS (3 hypotheses per asset)
5. PORTFOLIO STATE & DECISION FRAMEWORK
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from .alpha_setup_generator import AlphaSetup, AlphaSetupGenerator
from .narrative_analyzer import NarrativeAnalyzer, NarrativeClassification
from .pain_trade_analyzer import PainTradeAnalyzer, SqueezeAnalysis

logger = logging.getLogger(__name__)


class MultiCoinPromptService:
    """
    Enhanced Multi-Coin Prompt Service with NoF1-style analysis.

    Generates comprehensive prompts that include:
    - Multi-timeframe price structure
    - Funding rate and OI analysis
    - Narrative vs Reality classification
    - Pain trade / squeeze detection
    - 3-hypothesis alpha setups per asset
    - Explicit decision framework
    """

    def __init__(self, db=None):
        """Initialize with all analysis services."""
        self.db = db  # For compatibility
        self.narrative_analyzer = NarrativeAnalyzer()
        self.pain_trade_analyzer = PainTradeAnalyzer()
        self.alpha_setup_generator = AlphaSetupGenerator()

        # Coin mapping
        self.coin_mapping = {
            "BTC/USDT": "Bitcoin",
            "ETH/USDT": "Ethereum",
            "SOL/USDT": "Solana",
            "BNB/USDT": "BNB",
            "XRP/USDT": "XRP",
        }

    def get_simple_decision(
        self, bot, symbol, market_snapshot, market_regime, all_coins_data, bot_positions=None
    ):
        """
        Compatibility wrapper for SimpleLLMPromptService interface.
        """
        if all_coins_data is None:
            all_coins_data = {}
        if not isinstance(all_coins_data, dict):
            logger.warning(f"all_coins_data not a dict, converting to empty dict")
            all_coins_data = {}

        all_positions = bot_positions or []
        prompt_data = self.get_multi_coin_decision(
            bot=bot, all_coins_data=all_coins_data, all_positions=all_positions
        )

        return {
            "prompt": prompt_data["prompt"],
            "symbol": symbol,
            "timestamp": prompt_data.get("timestamp", ""),
        }

    def get_multi_coin_decision(
        self,
        bot,
        all_coins_data: Dict[str, Dict],
        all_positions: List,
        news_data: Optional[List[Dict]] = None,
        portfolio_state: Optional[Dict] = None,
    ) -> Dict:
        """
        Generate NoF1-style comprehensive multi-coin prompt.

        Args:
            bot: Bot instance
            all_coins_data: Dict mapping symbols to market data
            all_positions: List of open positions
            news_data: Optional list of news items from NewsService
            portfolio_state: Optional portfolio state dict

        Returns:
            Dict with 'prompt', 'timestamp', and metadata
        """
        if all_positions is None:
            all_positions = []
        if news_data is None:
            news_data = []

        # Get list of symbols
        symbols = list(all_coins_data.keys()) if all_coins_data else list(self.coin_mapping.keys())

        # Build position symbols set
        position_symbols = set()
        for pos in all_positions:
            if hasattr(pos, "symbol"):
                position_symbols.add(pos.symbol)
            elif isinstance(pos, dict) and "symbol" in pos:
                position_symbols.add(pos["symbol"])

        # Prepare price data for narrative analysis
        price_data = self._prepare_price_data(all_coins_data)

        # Run analyses
        analyzed_news = self.narrative_analyzer.analyze_news_vs_reality(
            news_items=news_data, price_data=price_data, symbols=symbols
        )

        squeeze_analyses = {}
        crowded_trades = {}
        alpha_setups = {}

        for symbol in symbols:
            if symbol not in all_coins_data:
                continue

            market_data = all_coins_data[symbol]

            # Get narrative classification for this symbol
            narrative_class = "NEUTRAL"
            if symbol in analyzed_news and analyzed_news[symbol]:
                narrative_class = analyzed_news[symbol][0].get("classification", "NEUTRAL")

            # Squeeze analysis
            squeeze_analyses[symbol] = self._analyze_squeeze(symbol, market_data)

            # Crowded trade detection
            crowded_trades[symbol] = self.pain_trade_analyzer.detect_crowded_trades(
                symbol=symbol,
                funding_rate=market_data.get("funding_rate", 0),
                price_change_24h=self._calc_price_change(market_data, "24h"),
                narrative_sentiment=self._get_primary_sentiment(analyzed_news.get(symbol, [])),
                volume_ratio=self._calc_volume_ratio(market_data),
            )

            # Alpha setup generation
            alpha_setups[symbol] = self._generate_alpha_setup(symbol, market_data, narrative_class)

        # Build the prompt
        prompt = self._build_comprehensive_prompt(
            symbols=symbols,
            all_coins_data=all_coins_data,
            all_positions=all_positions,
            position_symbols=position_symbols,
            analyzed_news=analyzed_news,
            squeeze_analyses=squeeze_analyses,
            crowded_trades=crowded_trades,
            alpha_setups=alpha_setups,
            portfolio_state=portfolio_state,
        )

        return {
            "prompt": prompt,
            "timestamp": datetime.utcnow().isoformat(),
            "symbols_count": len(symbols),
            "positions_count": len(all_positions),
            "has_news": len(news_data) > 0,
            "squeeze_detected": any(
                s.squeeze_type.value != "NO_SQUEEZE" for s in squeeze_analyses.values()
            ),
        }

    def _prepare_price_data(self, all_coins_data: Dict) -> Dict[str, Dict]:
        """Prepare price data structure for narrative analysis."""
        price_data = {}
        for symbol, data in all_coins_data.items():
            current = data.get("current_price", 0)
            # Estimate 1h ago price from price series if available
            price_series = data.get("price_series", [])
            price_1h_ago = price_series[-12] if len(price_series) > 12 else current  # 5min candles

            change_pct = ((current - price_1h_ago) / price_1h_ago * 100) if price_1h_ago > 0 else 0

            price_data[symbol] = {
                "current_price": current,
                "price_1h_ago": price_1h_ago,
                "change_pct": change_pct,
                "volume_ratio": self._calc_volume_ratio(data),
            }
        return price_data

    def _calc_price_change(self, market_data: Dict, period: str) -> float:
        """Calculate price change for a period."""
        current = market_data.get("current_price", 0)
        price_series = market_data.get("price_series", [])

        if period == "1h" and len(price_series) > 12:
            old_price = price_series[-12]
        elif period == "4h" and len(price_series) > 48:
            old_price = price_series[-48]
        elif period == "24h" and len(price_series) > 288:
            old_price = price_series[-288]
        else:
            old_price = price_series[0] if price_series else current

        return ((current - old_price) / old_price * 100) if old_price > 0 else 0

    def _calc_volume_ratio(self, market_data: Dict) -> float:
        """Calculate current volume vs average."""
        tech = market_data.get("technical_indicators", {}).get("1h", {})
        current_vol = tech.get("volume", 0)
        avg_vol = tech.get("avg_volume", 1)
        return current_vol / avg_vol if avg_vol > 0 else 1.0

    def _get_primary_sentiment(self, news_list: List[Dict]) -> str:
        """Get primary sentiment from news list."""
        if not news_list:
            return "neutral"
        return news_list[0].get("sentiment", "neutral")

    def _analyze_squeeze(self, symbol: str, market_data: Dict) -> SqueezeAnalysis:
        """Analyze squeeze potential for a symbol."""
        current = market_data.get("current_price", 0)
        price_series = market_data.get("price_series", [])

        price_1h_ago = price_series[-12] if len(price_series) > 12 else current
        price_4h_ago = price_series[-48] if len(price_series) > 48 else current

        # Get high/low from recent data
        recent_prices = price_series[-48:] if len(price_series) > 48 else price_series
        high_4h = max(recent_prices) if recent_prices else current
        low_4h = min(recent_prices) if recent_prices else current

        oi_data = market_data.get("open_interest", {})

        return self.pain_trade_analyzer.analyze_squeeze_potential(
            symbol=symbol,
            funding_rate=market_data.get("funding_rate", 0),
            open_interest=oi_data.get("latest", 0),
            avg_open_interest=oi_data.get("average", 1),
            current_price=current,
            price_1h_ago=price_1h_ago,
            price_4h_ago=price_4h_ago,
            high_4h=high_4h,
            low_4h=low_4h,
        )

    def _generate_alpha_setup(
        self, symbol: str, market_data: Dict, narrative_class: str
    ) -> AlphaSetup:
        """Generate alpha setup for a symbol."""
        current = market_data.get("current_price", 0)
        price_series = market_data.get("price_series", [])

        # Extract historical prices
        price_1h_ago = price_series[-12] if len(price_series) > 12 else current
        price_4h_ago = price_series[-48] if len(price_series) > 48 else current
        price_24h_ago = price_series[0] if price_series else current

        recent_prices = price_series[-48:] if len(price_series) > 48 else price_series
        high_4h = max(recent_prices) if recent_prices else current
        low_4h = min(recent_prices) if recent_prices else current
        high_24h = max(price_series) if price_series else current
        low_24h = min(price_series) if price_series else current

        # Get technicals
        tech_5m = market_data.get("technical_indicators", {}).get("5m", {})
        tech_1h = market_data.get("technical_indicators", {}).get("1h", {})

        oi_data = market_data.get("open_interest", {})

        return self.alpha_setup_generator.generate_setup(
            symbol=symbol,
            current_price=current,
            price_1h_ago=price_1h_ago,
            price_4h_ago=price_4h_ago,
            price_24h_ago=price_24h_ago,
            high_4h=high_4h,
            low_4h=low_4h,
            high_24h=high_24h,
            low_24h=low_24h,
            rsi_14=tech_1h.get("rsi14", 50),
            ema_20=tech_1h.get("ema20", current),
            ema_50=tech_1h.get("ema50", current),
            funding_rate=market_data.get("funding_rate", 0),
            open_interest=oi_data.get("latest", 0),
            avg_open_interest=oi_data.get("average", 1),
            volume_ratio=self._calc_volume_ratio(market_data),
            narrative_classification=narrative_class,
        )

    def _build_comprehensive_prompt(
        self,
        symbols: List[str],
        all_coins_data: Dict,
        all_positions: List,
        position_symbols: set,
        analyzed_news: Dict,
        squeeze_analyses: Dict[str, SqueezeAnalysis],
        crowded_trades: Dict,
        alpha_setups: Dict[str, AlphaSetup],
        portfolio_state: Optional[Dict],
    ) -> str:
        """Build the complete NoF1-style prompt."""
        lines = []

        # Header
        now = datetime.utcnow()
        lines.append("# CURRENT STATE OF MARKETS")
        lines.append(f"It is {now.strftime('%Y-%m-%d')} {now.strftime('%H:%M')} UTC.")
        lines.append("")

        # Section 1: Raw Data Dashboard
        lines.append("## 1. RAW DATA DASHBOARD")
        lines.append("")

        for symbol in symbols:
            if symbol not in all_coins_data:
                continue

            data = all_coins_data[symbol]
            coin_name = self.coin_mapping.get(symbol, symbol.split("/")[0])

            current = data.get("current_price", 0)
            funding = data.get("funding_rate", 0)
            oi = data.get("open_interest", {}).get("latest", 0)

            tech_5m = data.get("technical_indicators", {}).get("5m", {})
            tech_1h = data.get("technical_indicators", {}).get("1h", {})

            # Price structure
            price_series = data.get("price_series", [])
            recent = price_series[-48:] if len(price_series) > 48 else price_series
            high_4h = max(recent) if recent else current
            low_4h = min(recent) if recent else current

            lines.append(f"### {coin_name} ({symbol})")
            lines.append(
                f"- **Price**: ${current:,.4f} (4H Range: ${low_4h:,.4f} - ${high_4h:,.4f})"
            )
            lines.append(f"- **Net Funding**: {funding:+.4f}% / 8h")
            lines.append(f"- **Open Interest**: {oi:,.0f}")
            lines.append(
                f"- **RSI(14)**: {tech_1h.get('rsi14', 50):.1f} | **EMA20**: ${tech_1h.get('ema20', 0):,.4f} | **EMA50**: ${tech_1h.get('ema50', 0):,.4f}"
            )
            lines.append(f"- **Vol Ratio**: {self._calc_volume_ratio(data):.2f}x average")
            lines.append("")

        # Section 2: Narrative vs Reality
        lines.append(self.narrative_analyzer.format_for_prompt(analyzed_news))

        # Section 3: Pain Trade Analysis
        lines.append(self.pain_trade_analyzer.format_for_prompt(squeeze_analyses, crowded_trades))

        # Section 4: Alpha Setups
        lines.append(self.alpha_setup_generator.format_for_prompt(alpha_setups))

        # Section 5: Portfolio State
        lines.append("## 5. CURRENT PORTFOLIO STATE")
        lines.append("")

        if portfolio_state:
            lines.append(f"- **Available Capital**: ${float(portfolio_state.get('cash', 0)):,.2f}")
            lines.append(f"- **Total NAV**: ${float(portfolio_state.get('total_value', 0)):,.2f}")
            lines.append(
                f"- **Unrealized PnL**: ${float(portfolio_state.get('unrealized_pnl', 0)):+,.2f}"
            )
        else:
            lines.append("- Portfolio state not provided")
        lines.append("")

        # Open Positions - Enhanced for LLM exit analysis
        if all_positions:
            lines.append("### Open Positions (ANALYZE EACH FOR EXIT)")
            lines.append("")
            for pos in all_positions:
                if hasattr(pos, "symbol"):
                    coin = self.coin_mapping.get(pos.symbol, pos.symbol)
                    side = pos.side.upper() if hasattr(pos, "side") else "UNKNOWN"
                    qty = float(pos.quantity) if hasattr(pos, "quantity") else 0
                    entry = float(pos.entry_price) if hasattr(pos, "entry_price") else 0
                    current = float(pos.current_price) if hasattr(pos, "current_price") else entry
                    sl = float(pos.stop_loss) if hasattr(pos, "stop_loss") else 0
                    tp = float(pos.take_profit) if hasattr(pos, "take_profit") else 0

                    # Calculate P&L
                    if side == "LONG":
                        pnl = (current - entry) * qty
                        sl_dist = ((sl - current) / current * 100) if current > 0 else 0
                        tp_dist = ((tp - current) / current * 100) if current > 0 else 0
                    else:
                        pnl = (entry - current) * qty
                        sl_dist = ((current - sl) / current * 100) if current > 0 else 0
                        tp_dist = ((current - tp) / current * 100) if current > 0 else 0
                    pnl_pct = (pnl / (entry * qty) * 100) if entry * qty > 0 else 0

                    # Calculate hold time
                    hold_hours = 0.0
                    if hasattr(pos, "opened_at") and pos.opened_at:
                        hold_duration = datetime.utcnow() - pos.opened_at
                        hold_hours = hold_duration.total_seconds() / 3600

                    lines.append(f"**{coin}** ({pos.symbol}):")
                    lines.append(f"  - Side: {side} | Qty: {qty:.6f}")
                    lines.append(f"  - Entry: ${entry:,.2f} → Current: ${current:,.2f}")
                    lines.append(f"  - **Unrealized P&L: ${pnl:+,.2f} ({pnl_pct:+.2f}%)**")
                    lines.append(
                        f"  - SL: ${sl:,.2f} ({sl_dist:+.1f}% away) | TP: ${tp:,.2f} ({tp_dist:+.1f}% away)"
                    )
                    lines.append(f"  - Hold time: {hold_hours:.1f} hours")
                    lines.append(f"  - **⚠️ DECIDE: HOLD or CLOSE this position?**")
                    lines.append("")
                elif isinstance(pos, dict):
                    symbol = pos.get("symbol", "UNKNOWN")
                    coin = self.coin_mapping.get(symbol, symbol)
                    lines.append(
                        f"- **{coin}**: {pos.get('side', 'LONG').upper()} @ ${pos.get('entry_price', 0):,.2f}"
                    )
            lines.append("")
        else:
            lines.append("### No Open Positions")
            lines.append("")

        # Section 6: Decision Framework
        lines.append("## DECISION FRAMEWORK")
        lines.append("")
        lines.append("### For OPEN positions:")
        lines.append("1. Is invalidation condition met? (Y/N)")
        lines.append("2. Is stop loss triggered? (Y/N)")
        lines.append("3. Has thesis fundamentally changed? (Y/N)")
        lines.append("→ If all N: **HOLD** with original SL/TP")
        lines.append("→ If any Y: **EXIT** with justification")
        lines.append("")
        lines.append("### For symbols WITHOUT position:")
        lines.append("1. Is there a clear edge? (confidence > 0.70)")
        lines.append("2. Does expected move exceed 0.15% fee hurdle?")
        lines.append("3. Is R:R > 1.5?")
        lines.append("4. Excessive correlation with existing positions?")
        lines.append("→ If all yes/no appropriately: **ENTRY** with calculated SL/TP/Size")
        lines.append("→ Otherwise: **HOLD** (no trade)")
        lines.append("")
        lines.append("### SHOW YOUR CALCULATIONS:")
        lines.append("- Margin = confidence_tier × available_capital")
        lines.append("- Notional = margin × leverage")
        lines.append("- Quantity = notional / entry_price")
        lines.append("- Stop Distance = entry_price × risk_factor")
        lines.append("- R:R = target_distance / stop_distance")
        lines.append("")

        # Response Format
        lines.append("## RESPONSE FORMAT")
        lines.append("")
        lines.append("Return a JSON object with keys for each symbol you are acting on.")
        lines.append("For **HOLD** (existing position): Copy existing SL/TP/invalidation")
        lines.append("For **EXIT**: Signal close with justification")
        lines.append("For **ENTRY**: Full trade parameters")
        lines.append("")
        lines.append("```json")
        lines.append("{")
        lines.append('  "BTC/USDT": {')
        lines.append('    "signal": "hold|buy_to_enter|sell_to_enter|close",')
        lines.append('    "confidence": 0.0-1.0,')
        lines.append('    "quantity": <float>,')
        lines.append('    "leverage": <int 1-20>,')
        lines.append('    "profit_target": <float>,')
        lines.append('    "stop_loss": <float>,')
        lines.append('    "invalidation_condition": "<string>",')
        lines.append('    "justification": "<1-3 sentences explaining the decision>"')
        lines.append("  }")
        lines.append("}")
        lines.append("```")

        return "\n".join(lines)

    def parse_multi_coin_response(
        self, response_text: str, target_symbols: Optional[List[str]] = None
    ) -> Dict:
        """
        Parse LLM response for multi-coin decisions.
        """
        if target_symbols is None:
            target_symbols = list(self.coin_mapping.keys())

        try:
            # Try direct JSON parse
            if response_text.strip().startswith("{"):
                data = json.loads(response_text)
                return data

            # Extract JSON from response
            start_brace = response_text.find("{")
            end_brace = response_text.rfind("}")

            if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
                json_part = response_text[start_brace : end_brace + 1]
                data = json.loads(json_part)
                return data
            else:
                logger.error(f"Could not find JSON in response: {response_text[:100]}...")
                return self._create_fallback_response(target_symbols)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return self._create_fallback_response(target_symbols)
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return self._create_fallback_response(target_symbols)

    def _create_fallback_response(self, symbols: List[str]) -> Dict:
        """Create fallback HOLD response for all symbols."""
        return {
            symbol: {
                "signal": "hold",
                "confidence": 0.50,
                "justification": "JSON parse error fallback - default HOLD",
            }
            for symbol in symbols
        }

    def get_decision_for_symbol(self, symbol: str, response_text: str) -> Dict:
        """Extract decision for a specific symbol from LLM response."""
        if not response_text.strip():
            return {
                "action": "hold",
                "confidence": 0.6,
                "reasoning": f"Empty LLM response for {symbol}, default HOLD",
            }

        try:
            decisions = self.parse_multi_coin_response(response_text, [symbol])

            if symbol in decisions:
                decision = decisions[symbol]
                return {
                    "action": decision.get("signal", "hold"),
                    "confidence": decision.get("confidence", 0.6),
                    "reasoning": decision.get(
                        "justification", decision.get("reasoning", f"Decision for {symbol}")
                    ),
                }
            else:
                return {
                    "action": "hold",
                    "confidence": 0.6,
                    "reasoning": f"Symbol {symbol} not found in LLM response, default HOLD",
                }
        except Exception as e:
            logger.warning(f"Error parsing {symbol}: {e}, fallback HOLD")
            return {
                "action": "hold",
                "confidence": 0.6,
                "reasoning": f"Parsing error for {symbol}, default HOLD",
            }

    def parse_simple_response(
        self, response_text: str, symbol: str, current_market_price: float = 0
    ) -> Dict:
        """Compatibility method for SimpleLLMPromptService interface."""
        return self.get_decision_for_symbol(symbol, response_text)
