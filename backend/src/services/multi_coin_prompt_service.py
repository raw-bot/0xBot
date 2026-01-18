"""
Multi-Coin Prompt Service - Generates comprehensive trading prompts with market analysis.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from .alpha_setup_generator import AlphaSetup, AlphaSetupGenerator
from .fvg_detector_service import get_fvg_detector
from .market_sentiment_service import MarketSentiment, get_sentiment_service
from .narrative_analyzer import NarrativeAnalyzer
from .pain_trade_analyzer import PainTradeAnalyzer, SqueezeAnalysis

logger = logging.getLogger(__name__)

COIN_MAPPING = {
    "BTC/USDT": "Bitcoin",
    "ETH/USDT": "Ethereum",
    "SOL/USDT": "Solana",
    "BNB/USDT": "BNB",
    "XRP/USDT": "XRP",
}


class MultiCoinPromptService:
    """Generates 0xBot-style multi-coin trading prompts with comprehensive analysis."""

    def __init__(self, db=None):
        self.db = db
        self.narrative_analyzer = NarrativeAnalyzer()
        self.pain_trade_analyzer = PainTradeAnalyzer()
        self.alpha_setup_generator = AlphaSetupGenerator()
        self.sentiment_service = get_sentiment_service()
        self.fvg_detector = get_fvg_detector()
        self.coin_mapping = COIN_MAPPING

    def get_simple_decision(
        self, bot, symbol, market_snapshot, market_regime, all_coins_data, bot_positions=None
    ):
        """Compatibility wrapper for SimpleLLMPromptService interface."""
        all_coins_data = all_coins_data if isinstance(all_coins_data, dict) else {}
        prompt_data = self.get_multi_coin_decision(
            bot=bot, all_coins_data=all_coins_data, all_positions=bot_positions or []
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
        sentiment_data: Optional[MarketSentiment] = None,
    ) -> Dict:
        """Generate comprehensive multi-coin prompt with all analysis sections."""
        all_positions = all_positions or []
        news_data = news_data or []
        symbols = list(all_coins_data.keys()) if all_coins_data else list(self.coin_mapping.keys())

        position_symbols = {
            pos.symbol if hasattr(pos, "symbol") else pos.get("symbol")
            for pos in all_positions
            if hasattr(pos, "symbol") or (isinstance(pos, dict) and "symbol" in pos)
        }

        price_data = self._prepare_price_data(all_coins_data)
        analyzed_news = self.narrative_analyzer.analyze_news_vs_reality(
            news_items=news_data, price_data=price_data, symbols=symbols
        )

        squeeze_analyses, crowded_trades, alpha_setups, fvg_analyses = {}, {}, {}, {}

        for symbol in symbols:
            if symbol not in all_coins_data:
                continue

            market_data = all_coins_data[symbol]
            news_for_symbol = analyzed_news.get(symbol, [])
            narrative_class = news_for_symbol[0].get("classification", "NEUTRAL") if news_for_symbol else "NEUTRAL"

            squeeze_analyses[symbol] = self._analyze_squeeze(symbol, market_data)
            crowded_trades[symbol] = self.pain_trade_analyzer.detect_crowded_trades(
                symbol=symbol,
                funding_rate=market_data.get("funding_rate", 0),
                price_change_24h=self._calc_price_change(market_data, "24h"),
                narrative_sentiment=self._get_primary_sentiment(news_for_symbol),
                volume_ratio=self._calc_volume_ratio(market_data),
            )
            alpha_setups[symbol] = self._generate_alpha_setup(symbol, market_data, narrative_class)
            fvg_analyses[symbol] = self._analyze_fvg(symbol, market_data)

        sentiment = sentiment_data or self.sentiment_service._cached_sentiment

        prompt = self._build_comprehensive_prompt(
            symbols=symbols,
            all_coins_data=all_coins_data,
            all_positions=all_positions,
            position_symbols=position_symbols,
            analyzed_news=analyzed_news,
            squeeze_analyses=squeeze_analyses,
            crowded_trades=crowded_trades,
            alpha_setups=alpha_setups,
            fvg_analyses=fvg_analyses,
            portfolio_state=portfolio_state,
            sentiment=sentiment,
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

    def _get_price_at_offset(self, market_data: Dict, offset: int) -> float:
        """Get price from series at offset candles back, or current price if unavailable."""
        current = market_data.get("current_price", 0)
        price_series = market_data.get("price_series", [])
        return price_series[-offset] if len(price_series) > offset else current

    def _get_price_range(self, market_data: Dict, lookback: int) -> tuple:
        """Get (high, low) from recent price series."""
        current = market_data.get("current_price", 0)
        price_series = market_data.get("price_series", [])
        recent = price_series[-lookback:] if len(price_series) > lookback else price_series
        if not recent:
            return current, current
        return max(recent), min(recent)

    def _prepare_price_data(self, all_coins_data: Dict) -> Dict[str, Dict]:
        """Prepare price data structure for narrative analysis."""
        price_data = {}
        for symbol, data in all_coins_data.items():
            current = data.get("current_price", 0)
            price_1h_ago = self._get_price_at_offset(data, 12)
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
        offsets = {"1h": 12, "4h": 48, "24h": 288}
        offset = offsets.get(period, 0)
        old_price = self._get_price_at_offset(market_data, offset) if offset else market_data.get("price_series", [current])[0]
        return ((current - old_price) / old_price * 100) if old_price > 0 else 0

    def _calc_volume_ratio(self, market_data: Dict) -> float:
        """Calculate current volume vs average."""
        tech = market_data.get("technical_indicators", {}).get("1h", {})
        avg_vol = tech.get("avg_volume", 1)
        return tech.get("volume", 0) / avg_vol if avg_vol > 0 else 1.0

    def _get_primary_sentiment(self, news_list: List[Dict]) -> str:
        """Get primary sentiment from news list."""
        return news_list[0].get("sentiment", "neutral") if news_list else "neutral"

    def _analyze_squeeze(self, symbol: str, market_data: Dict) -> SqueezeAnalysis:
        """Analyze squeeze potential for a symbol."""
        current = market_data.get("current_price", 0)
        high_4h, low_4h = self._get_price_range(market_data, 48)
        oi_data = market_data.get("open_interest", {})

        return self.pain_trade_analyzer.analyze_squeeze_potential(
            symbol=symbol,
            funding_rate=market_data.get("funding_rate", 0),
            open_interest=oi_data.get("latest", 0),
            avg_open_interest=oi_data.get("average", 1),
            current_price=current,
            price_1h_ago=self._get_price_at_offset(market_data, 12),
            price_4h_ago=self._get_price_at_offset(market_data, 48),
            high_4h=high_4h,
            low_4h=low_4h,
        )

    def _generate_alpha_setup(
        self, symbol: str, market_data: Dict, narrative_class: str
    ) -> AlphaSetup:
        """Generate alpha setup for a symbol."""
        current = market_data.get("current_price", 0)
        price_series = market_data.get("price_series", [])
        high_4h, low_4h = self._get_price_range(market_data, 48)
        high_24h = max(price_series) if price_series else current
        low_24h = min(price_series) if price_series else current
        tech_1h = market_data.get("technical_indicators", {}).get("1h", {})
        oi_data = market_data.get("open_interest", {})

        return self.alpha_setup_generator.generate_setup(
            symbol=symbol,
            current_price=current,
            price_1h_ago=self._get_price_at_offset(market_data, 12),
            price_4h_ago=self._get_price_at_offset(market_data, 48),
            price_24h_ago=price_series[0] if price_series else current,
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

    def _analyze_fvg(self, symbol: str, market_data: Dict) -> str:
        """Analyze Fair Value Gaps for a symbol."""
        ohlcv_data = market_data.get("ohlcv", [])
        if not ohlcv_data or len(ohlcv_data) < 3:
            return f"### FVG Analysis ({symbol})\nInsufficient data for FVG detection.\n"

        candles = [
            {
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "timestamp": c.datetime.isoformat(),
            }
            for c in ohlcv_data
        ]

        price_series = market_data.get("price_series", [])
        if price_series and len(price_series) > 20:
            range_high, range_low = max(price_series[-20:]), min(price_series[-20:])
        else:
            range_high = max(c["high"] for c in candles[-20:])
            range_low = min(c["low"] for c in candles[-20:])

        self.fvg_detector.detect_fvgs(symbol, candles, market_data.get("timeframe", "1h"))
        current_price = market_data.get("current_price", 0)
        if current_price > 0:
            self.fvg_detector.update_mitigation(symbol, current_price)

        return self.fvg_detector.format_for_prompt(symbol, range_high, range_low)

    def _format_position(self, pos) -> List[str]:
        """Format a single position for the prompt."""
        lines = []
        if hasattr(pos, "symbol"):
            coin = self.coin_mapping.get(pos.symbol, pos.symbol)
            side = getattr(pos, "side", "UNKNOWN").upper()
            qty = float(getattr(pos, "quantity", 0))
            entry = float(getattr(pos, "entry_price", 0))
            current = float(getattr(pos, "current_price", entry))
            sl = float(getattr(pos, "stop_loss", 0))
            tp = float(getattr(pos, "take_profit", 0))

            if side == "LONG":
                pnl = (current - entry) * qty
                sl_dist = ((sl - current) / current * 100) if current > 0 else 0
                tp_dist = ((tp - current) / current * 100) if current > 0 else 0
            else:
                pnl = (entry - current) * qty
                sl_dist = ((current - sl) / current * 100) if current > 0 else 0
                tp_dist = ((current - tp) / current * 100) if current > 0 else 0
            pnl_pct = (pnl / (entry * qty) * 100) if entry * qty > 0 else 0

            hold_hours = 0.0
            if hasattr(pos, "opened_at") and pos.opened_at:
                hold_hours = (datetime.utcnow() - pos.opened_at).total_seconds() / 3600

            lines.extend([
                f"**{coin}** ({pos.symbol}):",
                f"  - Side: {side} | Qty: {qty:.6f}",
                f"  - Entry: ${entry:,.2f} -> Current: ${current:,.2f}",
                f"  - **Unrealized P&L: ${pnl:+,.2f} ({pnl_pct:+.2f}%)**",
                f"  - SL: ${sl:,.2f} ({sl_dist:+.1f}% away) | TP: ${tp:,.2f} ({tp_dist:+.1f}% away)",
                f"  - Hold time: {hold_hours:.1f} hours",
                "  - **DECIDE: HOLD or CLOSE this position?**",
                "",
            ])
        elif isinstance(pos, dict):
            symbol = pos.get("symbol", "UNKNOWN")
            coin = self.coin_mapping.get(symbol, symbol)
            lines.append(f"- **{coin}**: {pos.get('side', 'LONG').upper()} @ ${pos.get('entry_price', 0):,.2f}")
        return lines

    def _get_directional_bias_text(self, sentiment: Optional[MarketSentiment]) -> List[str]:
        """Generate directional trading bias section based on sentiment."""
        lines = ["## DIRECTIONAL TRADING STRATEGY", ""]

        if sentiment and hasattr(sentiment, "fear_greed_value"):
            fg = sentiment.fear_greed_value
            if fg < 35:
                lines.extend([
                    "### MANDATORY SHORT BIAS (Fear & Greed < 35)",
                    "",
                    "**CRITICAL: You MUST prioritize SHORT trades!**",
                    "",
                    "The market is in FEAR mode. Historical data shows:",
                    "- 70% of price action is DOWN in Fear markets",
                    "- LONG trades have a much lower win rate now",
                    "- SHORT trades are the profitable play",
                    "",
                    "**MANDATORY RULES:**",
                    "1. DO NOT open new LONG positions (buy_to_enter)",
                    "2. LOOK for SHORT entries (sell_to_enter)",
                    "3. RSI > 55 = SHORT opportunity (not just > 70)",
                    "4. Any bounce to EMA20/50 = SHORT entry point",
                    "5. Price below EMA50 = stay SHORT biased",
                    "",
                    "**If you recommend buy_to_enter in Fear market,",
                    "you are going AGAINST the market = BAD TRADE.**",
                    "",
                ])
            elif fg > 65:
                lines.extend([
                    "### BULLISH BIAS ACTIVE (Fear & Greed > 65)",
                    "**PRIORITY: Look for LONG opportunities!**",
                    "- Market is greedy -> momentum favors longs",
                    "- RSI < 40 on any coin = potential LONG entry",
                    "- Dips are buying opportunities",
                ])
            else:
                lines.extend([
                    "### NEUTRAL MARKET (Fear & Greed 35-65)",
                    "**Use both LONG and SHORT based on technicals:**",
                    "- RSI > 70 = SHORT signal (overbought)",
                    "- RSI < 30 = LONG signal (oversold)",
                    "- Trade the range, not the trend",
                ])
        else:
            lines.append("### Directional Bias: NEUTRAL (no sentiment data)")

        lines.extend([
            "",
            "### SHORT Entry Criteria (sell_to_enter):",
            "- RSI(14) > 55 on 1H timeframe (lower threshold in Fear)",
            "- Price at or near resistance (EMA20/50)",
            "- Negative funding or neutral",
            "- Fear & Greed < 50 preferred",
            "- Use signal: `sell_to_enter` with leverage <= 3x",
            "",
            "### LONG Entry Criteria (buy_to_enter):",
            "- RSI(14) < 30 on 1H timeframe (oversold)",
            "- Price bouncing from strong support",
            "- Fear & Greed > 50 (not in fear mode)",
            "- Use signal: `buy_to_enter` with leverage up to 5x",
            "",
            "**THE BOT MUST NOT ONLY GO LONG!**",
            "**In Fear markets, SHORT trades are the PROFITABLE ones.**",
            "**Going LONG in a falling market = LOSING MONEY.**",
            "",
        ])
        return lines

    def _get_decision_framework_text(self) -> List[str]:
        """Generate the decision framework section."""
        return [
            "## DECISION FRAMEWORK",
            "",
            "**IMPORTANT: Analyze EACH symbol independently. Having an open position on one symbol should NOT prevent entries on other symbols if there is available capital.**",
            "",
            "### For OPEN positions:",
            "1. Is there DANGER detected? (incoming crash, major resistance, bad news)",
            "2. Is position LOSING money? (protection mode)",
            "3. Is profit SIGNIFICANT? (>=2.0% unrealized PnL)",
            "4. Is stop loss/take profit about to trigger?",
            "",
            "**EXIT RULES:**",
            "-> If LOSING (PnL < 0%) AND danger detected: **CLOSE** (protection)",
            "-> If profit >= 2.0% AND target reached: **CLOSE** (profit-taking)",
            "-> If profit < 2.0%: **HOLD** - let the profit run! Never exit micro-profits.",
            "-> If no danger AND losing < 2%: **HOLD** - give it time to develop",
            "",
            "**ANTI-OVERTRADING: NEVER exit recent positions prematurely!**",
            "- A position opened < 1 hour ago should NOT be closed unless:",
            "  1. SL/TP is about to be hit",
            "  2. MAJOR danger detected (crash, black swan event)",
            "- Let trades BREATHE. Markets fluctuate. Be patient.",
            "- TIME is not a reason to exit. Only MARKET CONDITIONS matter.",
            "",
            "**NEVER recommend CLOSE for small profits (<2.0%)! This is wasteful.**",
            "",
            "### For symbols WITHOUT position:",
            "",
            "**FEE AWARENESS & ECONOMIC VIABILITY:**",
            "",
            "**Fee Structure:**",
            "- Round-trip fees: 0.10% (0.05% entry + 0.05% exit)",
            "- Example: 35% position @ 5x leverage = $17,500 notional = ~$17.50 in fees",
            "- Minimum move to break even: 0.10% / leverage",
            "",
            "**YOUR DECISION FRAMEWORK:**",
            "",
            "You are the expert trader. The system will reject trades that LOSE money after fees,",
            "but otherwise trusts YOUR judgment on risk/reward.",
            "",
            "**Consider:**",
            "- Is the expected profit > fees? (Required to execute)",
            "- Is the profit worth the risk given your confidence level?",
            "- Small profit (0.8%) with 85% confidence? Your call.",
            "- Large profit (3%) with 50% confidence? Your call.",
            "- Better opportunity might come later? Wait.",
            "",
            "**Quality over quantity:**",
            "It's better to make 0 trades than a bad trade.",
            "If uncertain, the answer is HOLD. Wait for a clear edge.",
            "",
            "**Recommended entry criteria (not mandatory):**",
            "- Clear edge with confidence >= 0.65",
            "- R:R ratio >= 1.5 (reward at least 1.5x the risk)",
            "- Sufficient capital available",
            "- Trade makes strategic sense based on your market analysis",
            "",
            "**QUALITY OVER QUANTITY:**",
            "It is BETTER to make 0 trades than to make a bad trade.",
            "If unsure, the answer is HOLD. Wait for a better setup.",
            "",
            "### SHOW YOUR CALCULATIONS:",
            "- Margin = confidence_tier x available_capital",
            "- Notional = margin x leverage",
            "- Quantity = notional / entry_price",
            "- Stop Distance = entry_price x risk_factor",
            "- R:R = target_distance / stop_distance",
            "",
        ]

    def _get_response_format_text(self, symbols: List[str]) -> List[str]:
        """Generate the response format section."""
        lines = [
            "## RESPONSE FORMAT",
            "",
            f"**MANDATORY: Analyze ALL {len(symbols)} symbols: {', '.join(symbols)}**",
            "",
            "### Step 1: CHAIN OF THOUGHT (Required)",
            "Before making decisions, reason through each symbol:",
            "- What is the current trend? (bullish/bearish/neutral)",
            "- Is there a clear edge? (funding, OI, technicals)",
            "- What is the expected profit after fees?",
            "- What is my confidence level and why?",
            "",
            "### Step 2: OUTPUT YOUR DECISIONS",
            "After your analysis, output a JSON object with your decisions.",
            "",
            "**IMPORTANT RULES:**",
            "- `signal` must be EXACTLY ONE OF: `hold`, `buy_to_enter`, `sell_to_enter`, `close`",
            "- `confidence` must be a DECIMAL NUMBER like `0.75`, NOT a range",
            "- For `hold`: only signal, confidence, justification needed",
            "- For entries: include entry_price, stop_loss, take_profit, leverage, quantity, **invalidation_condition**",
            "",
            "**`invalidation_condition` (REQUIRED for all entries)**",
            "",
            "For EVERY new trade (buy_to_enter / sell_to_enter), you MUST provide:",
            '- `"invalidation_condition"`: A clear, specific condition that invalidates your thesis',
            "",
            "**Rules for invalidation_condition:**",
            "1. Must be CONTEXT-AWARE (based on current market structure)",
            "2. Must describe WHEN to exit even if SL/TP not hit",
            "3. Should reference price levels, funding changes, or market events",
            "",
            "**Examples of GOOD invalidation_condition:**",
            '- "Price breaks above $68,000 invalidating bearish structure"',
            '- "Funding rate flips positive above +0.01% signaling long squeeze risk"',
            '- "Price closes below $3,000 on 4H chart breaking support zone"',
            '- "RSI divergence disappears or breaks above 70 indicating momentum shift"',
            "",
            "**Examples of BAD invalidation_condition (too vague):**",
            '- "Market turns bearish"',
            '- "Trade goes against me"',
            '- "Conditions change"',
            "",
            "**Example for 2 symbols (adapt to your analysis):**",
            "```json",
            "{",
            f'  "{symbols[0]}": {{',
            '    "signal": "hold",',
            '    "confidence": 0.60,',
            '    "justification": "No clear edge, RSI neutral at 52"',
            "  },",
        ]
        if len(symbols) > 1:
            lines.extend([
                f'  "{symbols[1]}": {{',
                '    "signal": "buy_to_enter",',
                '    "confidence": 0.78,',
                '    "justification": "Strong support bounce with bullish FVG",',
                '    "entry_price": 3150.00,',
                '    "stop_loss": 3045.00,',
                '    "take_profit": 3400.00,',
                '    "leverage": 5,',
                '    "quantity": 0.5,',
                '    "invalidation_condition": "Price breaks below $3,000 support or funding turns negative below -0.01%"',
                "  }",
            ])
        lines.extend([
            "}",
            "```",
            "",
            "**DO NOT copy the example values! Use YOUR OWN analysis.**",
        ])
        return lines

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
        fvg_analyses: Dict[str, str],
        portfolio_state: Optional[Dict],
        sentiment: Optional[MarketSentiment] = None,
    ) -> str:
        """Build the complete 0xBot-style prompt."""
        now = datetime.utcnow()
        lines = [
            "# CURRENT STATE OF MARKETS",
            f"It is {now.strftime('%Y-%m-%d')} {now.strftime('%H:%M')} UTC.",
            "",
        ]

        # Section 0: Market Sentiment
        if sentiment:
            lines.append(self.sentiment_service.format_for_prompt(sentiment))
        else:
            lines.extend(["## 0. MARKET SENTIMENT CONTEXT", "", "*Sentiment data unavailable*", ""])

        # Section 1: Raw Data Dashboard
        lines.extend(["## 1. RAW DATA DASHBOARD", ""])
        for symbol in symbols:
            if symbol not in all_coins_data:
                continue
            data = all_coins_data[symbol]
            coin_name = self.coin_mapping.get(symbol, symbol.split("/")[0])
            current = data.get("current_price", 0)
            funding = data.get("funding_rate", 0)
            oi = data.get("open_interest", {}).get("latest", 0)
            tech_1h = data.get("technical_indicators", {}).get("1h", {})
            high_4h, low_4h = self._get_price_range(data, 48)

            lines.extend([
                f"### {coin_name} ({symbol})",
                f"- **Price**: ${current:,.2f} (4H Range: ${low_4h:,.2f} - ${high_4h:,.2f})",
                f"- **Net Funding**: {funding:+.4f}% / 8h",
                f"- **Open Interest**: {oi:,.0f}",
                f"- **RSI(14)**: {tech_1h.get('rsi14', 50):.1f} | **EMA20**: ${tech_1h.get('ema20', 0):,.2f} | **EMA50**: ${tech_1h.get('ema50', 0):,.2f}",
                f"- **Vol Ratio**: {self._calc_volume_ratio(data):.2f}x average",
                "",
            ])

        # Sections 2-4: Analyses from services
        lines.append(self.narrative_analyzer.format_for_prompt(analyzed_news))
        lines.append(self.pain_trade_analyzer.format_for_prompt(squeeze_analyses, crowded_trades))
        lines.append(self.alpha_setup_generator.format_for_prompt(alpha_setups))

        # Section 4.5: FVG Analysis
        lines.extend(["## 4.5 FAIR VALUE GAP (FVG) ANALYSIS", ""])
        for symbol in symbols:
            if symbol in fvg_analyses:
                lines.append(fvg_analyses[symbol])
        lines.append("")

        # Section 5: Portfolio State
        lines.extend(["## 5. CURRENT PORTFOLIO STATE", ""])
        if portfolio_state:
            lines.extend([
                f"- **Available Capital**: ${float(portfolio_state.get('cash', 0)):,.2f}",
                f"- **Total NAV**: ${float(portfolio_state.get('total_value', 0)):,.2f}",
                f"- **Unrealized PnL**: ${float(portfolio_state.get('unrealized_pnl', 0)):+,.2f}",
            ])
        else:
            lines.append("- Portfolio state not provided")
        lines.append("")

        # Open Positions
        if all_positions:
            lines.extend(["### Open Positions (ANALYZE EACH FOR EXIT)", ""])
            for pos in all_positions:
                lines.extend(self._format_position(pos))
            lines.append("")
        else:
            lines.extend(["### No Open Positions", ""])

        # Directional Strategy, Decision Framework, Response Format
        lines.extend(self._get_directional_bias_text(sentiment))
        lines.extend(self._get_decision_framework_text())
        lines.extend(self._get_response_format_text(symbols))

        return "\n".join(lines)

    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from response text."""
        text = text.strip()
        if text.startswith("{"):
            return json.loads(text)
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start:end + 1])
        return None

    def _create_fallback_response(self, symbols: List[str], reason: str = "default HOLD") -> Dict:
        """Create fallback HOLD response for all symbols."""
        return {
            symbol: {"signal": "hold", "confidence": 0.50, "justification": reason}
            for symbol in symbols
        }

    def parse_multi_coin_response(
        self, response_text: str, target_symbols: Optional[List[str]] = None
    ) -> Dict:
        """Parse LLM response for multi-coin decisions."""
        target_symbols = target_symbols or list(self.coin_mapping.keys())

        try:
            data = self._extract_json(response_text)
            if not data:
                logger.error(f"Could not find JSON in response: {response_text[:100]}...")
                return self._create_fallback_response(target_symbols, "JSON parse error")

            decisions = data.get("decisions", data)
            missing = [s for s in target_symbols if s not in decisions]
            if missing:
                logger.warning(f"LLM response missing {len(missing)} symbols: {missing}")
                for sym in missing:
                    decisions[sym] = {"signal": "hold", "confidence": 0.50, "justification": "Missing from response"}
                logger.info(f"Auto-filled {len(missing)} missing symbols with HOLD")

            return decisions if "decisions" not in data else data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return self._create_fallback_response(target_symbols, "JSON parse error")
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return self._create_fallback_response(target_symbols, "Parse error")

    def get_decision_for_symbol(self, symbol: str, response_text: str) -> Dict:
        """Extract decision for a specific symbol from LLM response."""
        default = {"action": "hold", "confidence": 0.6, "reasoning": f"Default HOLD for {symbol}"}
        if not response_text.strip():
            return {**default, "reasoning": f"Empty LLM response for {symbol}"}

        try:
            decisions = self.parse_multi_coin_response(response_text, [symbol])
            if symbol not in decisions:
                return {**default, "reasoning": f"Symbol {symbol} not in response"}
            d = decisions[symbol]
            return {
                "action": d.get("signal", "hold"),
                "confidence": d.get("confidence", 0.6),
                "reasoning": d.get("justification", d.get("reasoning", f"Decision for {symbol}")),
            }
        except Exception as e:
            logger.warning(f"Error parsing {symbol}: {e}")
            return {**default, "reasoning": f"Parsing error for {symbol}"}

    def parse_simple_response(self, response_text: str, symbol: str, current_market_price: float = 0) -> Dict:
        """Compatibility method for SimpleLLMPromptService interface."""
        return self.get_decision_for_symbol(symbol, response_text)
