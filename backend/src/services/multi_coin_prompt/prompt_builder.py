"""
Prompt Builder - Generates multi-coin trading prompts with market context.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..market_sentiment_service import MarketSentiment


class PromptBuilder:
    """Builds comprehensive multi-coin trading prompts."""

    COIN_MAPPING = {
        "BTC/USDT": "Bitcoin",
        "ETH/USDT": "Ethereum",
        "SOL/USDT": "Solana",
        "BNB/USDT": "BNB",
        "XRP/USDT": "XRP",
    }

    def __init__(self) -> None:
        """Initialize PromptBuilder."""
        self.coin_mapping = self.COIN_MAPPING

    def build_prompt(
        self,
        symbols: List[str],
        market_data_formatted: str,
        news_analysis: str,
        pain_trades_analysis: str,
        alpha_setups_analysis: str,
        fvg_analysis: str,
        portfolio_state: Optional[Dict[str, Any]],
        positions_text: str,
        sentiment: Optional[MarketSentiment] = None,
    ) -> str:
        """Build complete prompt from pre-formatted sections."""
        now = datetime.utcnow()
        lines = [
            "# CURRENT STATE OF MARKETS",
            f"It is {now.strftime('%Y-%m-%d')} {now.strftime('%H:%M')} UTC.",
            "",
        ]

        # Section 0: Market Sentiment
        if sentiment:
            # Assume sentiment_service.format_for_prompt is available
            lines.append("## 0. MARKET SENTIMENT CONTEXT")
            lines.append("*Sentiment data provided*")
            lines.append("")
        else:
            lines.extend(["## 0. MARKET SENTIMENT CONTEXT", "", "*Sentiment data unavailable*", ""])

        # Section 1: Raw Data Dashboard
        lines.extend(["## 1. RAW DATA DASHBOARD", ""])
        lines.append(market_data_formatted)
        lines.append("")

        # Sections 2-4: Analyses from services
        lines.append(news_analysis)
        lines.append(pain_trades_analysis)
        lines.append(alpha_setups_analysis)

        # Section 4.5: FVG Analysis
        lines.extend(["## 4.5 FAIR VALUE GAP (FVG) ANALYSIS", ""])
        lines.append(fvg_analysis)
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
        lines.extend(["### Open Positions (ANALYZE EACH FOR EXIT)", ""])
        lines.append(positions_text)
        lines.append("")

        # Directional Strategy, Decision Framework, Response Format
        lines.extend(self._get_directional_bias_text(sentiment))
        lines.extend(self._get_decision_framework_text())
        lines.extend(self._get_response_format_text(symbols))

        return "\n".join(lines)

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
