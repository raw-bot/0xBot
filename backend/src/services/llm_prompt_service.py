"""LLM Prompt service V2.1 - Compatible Hybrid (Qwen3-inspired)."""

from decimal import Decimal
from typing import Optional, Dict, Any

from ..models.position import Position
from ..core.logger import get_logger

logger = get_logger(__name__)


class LLMPromptService:
    """Service for building prompts for LLM market analysis - V2.1 Compatible."""
    
    @staticmethod
    def build_market_prompt(
        symbol: str,
        market_data: dict,
        indicators: dict,
        positions: list[Position],
        portfolio: dict,
        risk_params: dict,
        indicators_4h: Optional[dict] = None  # NOUVEAU: Indicateurs 4H
    ) -> str:
        """
        Build an optimized market analysis prompt (V2.1 - Compatible format).
        
        Changes from V1:
        - Added multi-timeframe analysis (3min + 4h)
        - Added invalidation_condition requirement
        - Structured decision framework
        - COMPATIBLE with existing JSON parser
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            market_data: Current market data (price, volume, etc.)
            indicators: Technical indicators for 3min timeframe
            positions: List of current open positions
            portfolio: Portfolio state (cash, total_value, etc.)
            risk_params: Risk management parameters
            indicators_4h: Technical indicators for 4h timeframe (optional)
            
        Returns:
            Formatted prompt string
        """
        # Extract current market data
        current_price = market_data.get('current_price', 0)
        funding_rate = market_data.get('funding_rate', 0)
        
        # Build market data section (with multi-timeframe if available)
        market_section = LLMPromptService._build_market_section_v2(
            symbol, current_price, funding_rate, indicators, indicators_4h
        )
        
        # Build positions section
        positions_section = LLMPromptService._build_positions_section(positions)
        
        # Build portfolio section
        portfolio_section = LLMPromptService._build_portfolio_section(portfolio)
        
        # Build risk parameters section
        risk_section = LLMPromptService._build_risk_section(risk_params)
        
        # Build complete prompt
        prompt = f"""You are an expert crypto trading AI with a proven track record. Your goal is to identify high-probability setups and execute with discipline.

═══════════════════════════════════════════════════════
MARKET DATA - MULTI-TIMEFRAME ANALYSIS
═══════════════════════════════════════════════════════

{market_section}

═══════════════════════════════════════════════════════
CURRENT POSITIONS & EXPOSURE
═══════════════════════════════════════════════════════

{positions_section}

═══════════════════════════════════════════════════════
PORTFOLIO STATE
═══════════════════════════════════════════════════════

{portfolio_section}

═══════════════════════════════════════════════════════
RISK MANAGEMENT CONSTRAINTS (MANDATORY)
═══════════════════════════════════════════════════════

{risk_section}

You MUST respect these constraints. Any trade violating them will be rejected.

═══════════════════════════════════════════════════════
TRADING FRAMEWORK & DECISION PROCESS
═══════════════════════════════════════════════════════

STEP 1: TREND ANALYSIS (Multi-Timeframe)
• 1H Context: What's the bigger picture trend?
  - EMA 20 vs 50: Bullish if 20 > 50, Bearish if 20 < 50
  - MACD 1H: Trending up or down?

• 5MIN Entry Timing: Is this a good entry point?
  - Price vs EMA 20: Are we near support/resistance?
  - RSI: Not overbought (>70) or oversold (<30) unless divergence
  - MACD: Momentum confirming direction?

STEP 2: CONFLUENCE CHECK
Strong setups have 3+ confirming factors:
✓ Trend alignment (1H and 5min agree)
✓ Momentum (MACD bullish/bearish)
✓ Price structure (near support/resistance)
✓ RSI confirmation (neutral range or divergence)

STEP 3: INVALIDATION CONDITION
Every trade MUST have a clear invalidation condition.
This is the TECHNICAL REASON why the trade would be wrong.
Example: "1-hour close below 105000" or "Break of ascending trendline"

STEP 4: RISK/REWARD CALCULATION
• Where would this trade be WRONG? → Invalidation level
• Where's the logical stop loss? → Based on structure
• Where's the realistic profit target? → Based on resistance/support
• Is R/R ratio favorable? Minimum 1.5:1, ideally 2:1+

STEP 5: POSITION SIZING DECISION
Default strategy (disciplined approach):
• Position size: 10% of available capital (INCREASED for better impact)
• Stop loss: 2% from entry (TIGHTER for better risk control)
• Take profit: 4% from entry (2:1 R/R maintained)

You MAY adjust these values ONLY if you have strong justification:
• High conviction (0.8+ confidence) + strong confluence → up to 15% position
• High volatility (wide Bollinger Bands) → tighter stops (1.5%) or smaller size (5%)
• Weak signal (0.5-0.6 confidence) → smaller position (5-7%)

═══════════════════════════════════════════════════════
RESPONSE FORMAT (JSON ONLY, NO OTHER TEXT)
═══════════════════════════════════════════════════════

Provide your decision as a JSON object with this EXACT structure:

{{
  "action": "hold" | "entry" | "exit" | "close_position",
  "symbol": "{symbol}",
  "side": "long" | "short" | null,
  "size_pct": 0.05,
  "stop_loss_pct": 0.03,
  "take_profit_pct": 0.06,
  "confidence": 0.75,
  "invalidation_condition": "Technical condition that invalidates this trade (e.g., '4-hour close below 105000', 'Break of support at 108500')",
  "reasoning": "Comprehensive explanation covering: (1) Multi-timeframe analysis (what 4H and 3min are telling you), (2) Confluence factors (3+ confirming signals), (3) Why this specific entry/exit makes sense, (4) What would make you wrong (invalidation), (5) Why these parameters (size, stops, targets) are optimal for THIS setup.",
  "key_factors": [
    "Primary signal from 4H timeframe",
    "Confirming signal from 3min timeframe", 
    "Additional confluence factor"
  ]
}}

═══════════════════════════════════════════════════════
PARAMETER GUIDELINES
═══════════════════════════════════════════════════════

• size_pct: Default 0.10 (10%). Adjust to 0.05-0.15 based on conviction
• stop_loss_pct: Default 0.02 (2%). Adjust to 0.015-0.03 based on volatility
• take_profit_pct: Default 0.04 (4%). Adjust to 0.03-0.08 for better R/R
• confidence: 0-0.4 (no trade), 0.4-0.6 (small), 0.6-0.8 (standard), 0.8-1.0 (high)
• invalidation_condition: MANDATORY - Always provide clear technical reason

═══════════════════════════════════════════════════════
ACTION RULES
═══════════════════════════════════════════════════════

"hold":
  - No actionable setup right now
  - Conflicting signals between timeframes
  - Wait for better risk/reward
  - Do NOT enter just to "do something"
  - BUT: If you have an open position, ALWAYS evaluate if it should be exited!

"entry":
  - Strong setup with 3+ confluence factors
  - 1H and 5min timeframes ALIGNED
  - Favorable risk/reward (min 1.5:1)
  - Clear invalidation level identified
  - NO open positions OR new opportunity is significantly better

"exit":
  - Position target reached (take profit hit)
  - Stop loss approached or invalidation triggered
  - RSI shows extreme overbought (>75) on long positions
  - RSI shows extreme oversold (<25) on short positions
  - Momentum divergence (MACD crosses against position)
  - Trend reversal on 1H timeframe
  - Position held >2 hours with minimal profit (<0.5%)
  - Any sign of weakness in the original thesis

"close_position":
  - Emergency exit when invalidation condition met
  - Severe market conditions or major trend reversal

═══════════════════════════════════════════════════════
CRITICAL RULES (Non-Negotiable)
═══════════════════════════════════════════════════════

1. INVALIDATION CONDITION IS MANDATORY
   Every entry must have "invalidation_condition" filled.
   This is the REASON behind the stop, not just a price.

2. MULTI-TIMEFRAME CONFIRMATION
   Check that 1H context supports 5min entry.
   Don't fight the 1H trend on 5min entries.
   If timeframes conflict → HOLD.

3. CONFLUENCE REQUIRED
   Need 3+ confirming factors for entry.
   Don't enter on a single indicator.

4. EXPLAIN YOUR PARAMETERS
   In reasoning, justify any deviation from defaults (5%/3%/6%).
   If using different values, explain why.

5. RESPECT RISK CONSTRAINTS
   Never violate max_position_pct, max_drawdown, max_trades_per_day.

6. EXIT DISCIPLINE IS CRITICAL
   When you have an open position, ALWAYS analyze if it should be closed.
   Don't just default to "hold" - actively decide: keep or exit?
   Reasons to exit include:
   - Original thesis invalidated
   - Better opportunity elsewhere
   - Risk/reward no longer favorable
   - Time-based: position held too long without movement
   - Technical: indicators turning against the position

═══════════════════════════════════════════════════════

Analyze the market data above and provide your trading decision as a JSON object.

Focus on QUALITY over QUANTITY. It's better to wait for a perfect setup than force marginal trades.

Remember: Consistent, risk-managed returns - not gambling on every move.

⚠️ IMPORTANT FOR OPEN POSITIONS:
If you currently have an open position, you MUST actively decide between:
1. Keep the position (action: "hold") - only if thesis is still valid
2. Exit the position (action: "exit") - if conditions changed or target/stop approached

Do NOT passively "hold" without actively checking exit conditions!

Respond ONLY with the JSON object, no additional text."""
        
        logger.debug(f"Built V2.1 compatible prompt for {symbol}")
        return prompt
    
    @staticmethod
    def _build_market_section_v2(
        symbol: str,
        current_price: Decimal,
        funding_rate: float,
        indicators: dict,
        indicators_4h: Optional[dict] = None
    ) -> str:
        """Build enhanced market section with multi-timeframe data."""
        
        # 3-MINUTE TIMEFRAME (Entry Timing)
        ema_20_3m = indicators.get('ema_20')
        ema_50_3m = indicators.get('ema_50')
        rsi_3m = indicators.get('rsi_14')
        macd_3m = indicators.get('macd', {})
        bb_3m = indicators.get('bb', {})
        
        # Determine 3min trend
        trend_3m = "N/A"
        if ema_20_3m and ema_50_3m:
            trend_3m = "Bullish" if ema_20_3m > ema_50_3m else "Bearish"
        
        # RSI state 3min
        rsi_state_3m = "N/A"
        if rsi_3m:
            if rsi_3m < 30:
                rsi_state_3m = "Oversold"
            elif rsi_3m > 70:
                rsi_state_3m = "Overbought"
            else:
                rsi_state_3m = "Neutral"
        
        # MACD signal 3min
        macd_val_3m = macd_3m.get('macd')
        signal_val_3m = macd_3m.get('signal')
        macd_signal_3m = "N/A"
        if macd_val_3m is not None and signal_val_3m is not None:
            macd_signal_3m = "Bullish" if macd_val_3m > signal_val_3m else "Bearish"
        
        # Build base section
        section = f"""
📊 {symbol} - Current Price: ${current_price:,.2f}
Funding Rate: {funding_rate:.4%}

┌─────────────────────────────────────────────────────────────┐
│ 5-MINUTE TIMEFRAME (Entry Timing)                           │
└─────────────────────────────────────────────────────────────┘

Trend Analysis:
• EMA(20): {f'${ema_20_3m:,.2f}' if ema_20_3m else 'N/A'}
• EMA(50): {f'${ema_50_3m:,.2f}' if ema_50_3m else 'N/A'}
• Trend Direction: {trend_3m}

Momentum:
• MACD: {f'{macd_val_3m:.2f}' if macd_val_3m else 'N/A'}
• Signal: {f'{signal_val_3m:.2f}' if signal_val_3m else 'N/A'}
• MACD Signal: {macd_signal_3m}

Oscillators:
• RSI(14): {f'{rsi_3m:.1f}' if rsi_3m else 'N/A'} - {rsi_state_3m}

Price Levels:
• Bollinger Upper: {f'${bb_3m.get("upper"):,.2f}' if bb_3m.get("upper") else 'N/A'}
• Bollinger Middle: {f'${bb_3m.get("middle"):,.2f}' if bb_3m.get("middle") else 'N/A'}
• Bollinger Lower: {f'${bb_3m.get("lower"):,.2f}' if bb_3m.get("lower") else 'N/A'}"""
        
        # Add 1H timeframe if available
        if indicators_4h:
            ema_20_1h = indicators_4h.get('ema_20')
            ema_50_1h = indicators_4h.get('ema_50')
            rsi_1h = indicators_4h.get('rsi_14')
            macd_1h = indicators_4h.get('macd', {})
            
            # Determine 1h trend
            trend_1h = "N/A"
            if ema_20_1h and ema_50_1h:
                trend_1h = "Bullish" if ema_20_1h > ema_50_1h else "Bearish"
            
            # RSI state 1h
            rsi_state_1h = "N/A"
            if rsi_1h:
                if rsi_1h < 30:
                    rsi_state_1h = "Oversold"
                elif rsi_1h > 70:
                    rsi_state_1h = "Overbought"
                else:
                    rsi_state_1h = "Neutral"
            
            # MACD signal 1h
            macd_val_1h = macd_1h.get('macd')
            signal_val_1h = macd_1h.get('signal')
            macd_signal_1h = "N/A"
            if macd_val_1h is not None and signal_val_1h is not None:
                macd_signal_1h = "Bullish" if macd_val_1h > signal_val_1h else "Bearish"
            
            # Confluence check
            alignment = "✓ ALIGNED" if trend_3m == trend_1h else "✗ CONFLICTING"
            
            section += f"""

┌─────────────────────────────────────────────────────────────┐
│ 1-HOUR TIMEFRAME (Market Context)                           │
└─────────────────────────────────────────────────────────────┘

Trend Analysis:
• EMA(20): {f'${ema_20_1h:,.2f}' if ema_20_1h else 'N/A'}
• EMA(50): {f'${ema_50_1h:,.2f}' if ema_50_1h else 'N/A'}
• Trend Direction: {trend_1h}

Momentum:
• MACD: {f'{macd_val_1h:.2f}' if macd_val_1h else 'N/A'}
• Signal: {f'{signal_val_1h:.2f}' if signal_val_1h else 'N/A'}
• MACD Signal: {macd_signal_1h}

Oscillators:
• RSI(14): {f'{rsi_1h:.1f}' if rsi_1h else 'N/A'} - {rsi_state_1h}

┌─────────────────────────────────────────────────────────────┐
│ TIMEFRAME CONFLUENCE                                         │
└─────────────────────────────────────────────────────────────┘

1H Trend: {trend_1h} | 5M Trend: {trend_3m} → {alignment}"""
        else:
            # No 1H data available
            section += """

┌─────────────────────────────────────────────────────────────┐
│ 1-HOUR TIMEFRAME (Market Context)                           │
└─────────────────────────────────────────────────────────────┘

⚠️ 1-hour timeframe data not available - using 5min data only.
Consider: Use 5min trend as proxy but be more conservative with entries."""
        
        return section
    
    @staticmethod
    def _build_positions_section(positions: list[Position]) -> str:
        """Build the open positions section of the prompt."""
        if not positions:
            return """OPEN POSITIONS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
No open positions"""
        
        section = "OPEN POSITIONS:\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        for i, pos in enumerate(positions, 1):
            pnl = pos.unrealized_pnl
            pnl_pct = pos.unrealized_pnl_pct
            pnl_sign = "+" if pnl >= 0 else ""
            
            section += f"""
Position {i}:
- Symbol: {pos.symbol}
- Side: {pos.side.upper()}
- Quantity: {pos.quantity}
- Entry Price: ${pos.entry_price:,.2f}
- Current Price: ${pos.current_price:,.2f}
- Unrealized PnL: {pnl_sign}${pnl:,.2f} ({pnl_sign}{pnl_pct:.2f}%)
- Stop Loss: {f'${pos.stop_loss:,.2f}' if pos.stop_loss else 'Not set'}
- Take Profit: {f'${pos.take_profit:,.2f}' if pos.take_profit else 'Not set'}"""
        
        return section
    
    @staticmethod
    def _build_portfolio_section(portfolio: dict) -> str:
        """Build the portfolio section of the prompt."""
        total_value = portfolio.get('total_value', 0)
        cash = portfolio.get('cash', 0)
        total_pnl = portfolio.get('total_pnl', 0)
        realized_pnl = portfolio.get('realized_pnl', 0)
        unrealized_pnl = portfolio.get('unrealized_pnl', 0)
        
        pnl_sign = "+" if total_pnl >= 0 else ""
        
        section = f"""PORTFOLIO STATE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Value: ${total_value:,.2f}
Available Cash: ${cash:,.2f}
Total PnL: {pnl_sign}${total_pnl:,.2f}
- Realized PnL: {pnl_sign if realized_pnl >= 0 else ""}${realized_pnl:,.2f}
- Unrealized PnL: {pnl_sign if unrealized_pnl >= 0 else ""}${unrealized_pnl:,.2f}"""
        
        return section
    
    @staticmethod
    def _build_risk_section(risk_params: dict) -> str:
        """Build the risk management section of the prompt."""
        max_position = risk_params.get('max_position_pct', 0.10)
        max_drawdown = risk_params.get('max_drawdown_pct', 0.20)
        max_trades = risk_params.get('max_trades_per_day', 10)
        
        section = f"""RISK PARAMETERS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Max Position Size: {max_position:.1%} of capital
Max Drawdown: {max_drawdown:.1%}
Max Trades Per Day: {max_trades}

You MUST respect these constraints in all decisions."""
        
        return section
    
    @staticmethod
    def build_emergency_close_prompt(
        positions: list[Position],
        reason: str
    ) -> str:
        """
        Build a prompt for emergency position closing.
        
        Args:
            positions: List of positions to close
            reason: Reason for emergency close
            
        Returns:
            Emergency close prompt
        """
        positions_list = "\n".join([
            f"- {pos.symbol} {pos.side.upper()}: {pos.quantity} @ ${pos.entry_price}"
            for pos in positions
        ])
        
        prompt = f"""EMERGENCY POSITION CLOSURE REQUIRED

Reason: {reason}

Positions to close:
{positions_list}

Provide a JSON response with close orders for all positions:
{{
  "action": "emergency_close_all",
  "positions": [
    {{
      "position_id": "uuid",
      "symbol": "BTC/USDT",
      "close_order": "market"
    }}
  ],
  "reasoning": "Emergency closure due to {reason}"
}}"""
        
        return prompt
    
    @staticmethod
    def build_multi_coin_context_section(
        market_context: Dict[str, Any]
    ) -> str:
        """
        Build a section describing multi-coin market context.
        
        Args:
            market_context: Output from MarketAnalysisService.get_comprehensive_market_context()
            
        Returns:
            Formatted string with multi-coin analysis
        """
        if not market_context or not market_context.get('regime'):
            return ""
        
        regime_info = market_context.get('regime', {})
        breadth_info = market_context.get('breadth', {})
        flow_info = market_context.get('capital_flows', {})
        btc_dominance = market_context.get('btc_dominance', 0)
        correlations = market_context.get('correlations', {})
        
        # Format regime
        regime = regime_info.get('regime', 'unknown')
        confidence = regime_info.get('confidence', 0)
        signals = regime_info.get('signals', {})
        
        # Format breadth
        ad_ratio = breadth_info.get('advance_decline_ratio', 0)
        advancing = breadth_info.get('advancing', 0)
        declining = breadth_info.get('declining', 0)
        breadth_strong = breadth_info.get('breadth_strong', False)
        
        # Format flows
        dominant_flow = flow_info.get('dominant_flow', 'unknown')
        btc_inflow = flow_info.get('btc_inflow', False)
        alt_inflow = flow_info.get('alt_inflow', False)
        
        # Build correlation summary
        corr_summary = ""
        if correlations:
            # Get average correlation
            all_corrs = []
            for symbol1, corr_dict in correlations.items():
                for symbol2, corr_val in corr_dict.items():
                    if symbol1 != symbol2:
                        all_corrs.append(corr_val)
            avg_corr = sum(all_corrs) / len(all_corrs) if all_corrs else 0
            
            corr_summary = f"""
Average Cross-Asset Correlation: {avg_corr:.2f} {"(High - assets moving together)" if avg_corr > 0.7 else "(Low - assets independent)" if avg_corr < 0.3 else "(Moderate)"}
"""
            # Add specific correlations if available
            btc_key = next((k for k in correlations.keys() if 'BTC' in k), None)
            if btc_key and len(correlations) > 1:
                corr_summary += "\nBTC Correlations with other assets:\n"
                for symbol, corr_val in correlations[btc_key].items():
                    if 'BTC' not in symbol:
                        corr_summary += f"  • {symbol}: {corr_val:.2f}\n"
        
        section = f"""
┌─────────────────────────────────────────────────────────────┐
│ MULTI-COIN MARKET CONTEXT                                    │
└─────────────────────────────────────────────────────────────┘

🌍 Market Regime: {regime.upper().replace('_', '-')} (Confidence: {confidence:.0%})
  • Avg Correlation: {signals.get('avg_correlation', 0):.2f}
  • Avg Volatility: {signals.get('avg_volatility', 0):.2%}
  • BTC Performance: {signals.get('btc_performance', 0):+.2%}
  • Alt Performance: {signals.get('alt_performance', 0):+.2%}
  
💹 Market Breadth:
  • Advance/Decline Ratio: {ad_ratio:.2f} ({advancing} up / {declining} down)
  • Breadth: {"STRONG" if breadth_strong else "WEAK"}
  • Average Change: {breadth_info.get('average_change', 0):+.2%}

💰 Capital Flows:
  • Dominant Flow: {dominant_flow.upper().replace('_', ' ')}
  • BTC: {"📈 Inflow" if btc_inflow else "📉 Outflow"}
  • Alts: {"📈 Inflow" if alt_inflow else "📉 Outflow"}

📊 BTC Dominance: {btc_dominance:.1f}%
{corr_summary}

KEY INSIGHTS:
• {"Risk-On: Alts outperforming, favorable for alt entries" if regime == 'risk_on' else ""}
• {"Risk-Off: Flight to BTC, be cautious with alts" if regime == 'risk_off' else ""}
• {"Neutral: Mixed signals, be selective" if regime == 'neutral' else ""}
• {"Strong breadth supports bullish moves" if breadth_strong else "Weak breadth - be cautious on longs"}
• {"Capital rotating into BTC" if dominant_flow == 'into_btc' else ""}
• {"Capital rotating into alts" if dominant_flow == 'into_alts' else ""}
• {"Capital leaving crypto" if dominant_flow == 'out_of_crypto' else ""}
"""
        
        return section
    
    @staticmethod
    def build_enhanced_market_prompt(
        symbol: str,
        market_data: dict,
        indicators: dict,
        positions: list[Position],
        portfolio: dict,
        risk_params: dict,
        indicators_4h: Optional[dict] = None,
        market_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build enhanced prompt with multi-coin market context.
        
        Args:
            symbol: Trading pair
            market_data: Market data for this symbol
            indicators: Technical indicators
            positions: Current positions
            portfolio: Portfolio state
            risk_params: Risk parameters
            indicators_4h: 4H timeframe indicators
            market_context: Multi-coin market analysis from MarketAnalysisService
            
        Returns:
            Enhanced prompt with market context
        """
        # Build base prompt
        base_prompt = LLMPromptService.build_market_prompt(
            symbol=symbol,
            market_data=market_data,
            indicators=indicators,
            positions=positions,
            portfolio=portfolio,
            risk_params=risk_params,
            indicators_4h=indicators_4h
        )
        
        # If no market context, return base prompt
        if not market_context:
            return base_prompt
        
        # Build multi-coin context section
        multi_coin_section = LLMPromptService.build_multi_coin_context_section(market_context)
        
        # Insert multi-coin context after market data section
        # Find the position after "MARKET DATA" section
        market_section_end = base_prompt.find("═══════════════════════════════════════════════════════\nCURRENT POSITIONS")
        
        if market_section_end != -1:
            enhanced_prompt = (
                base_prompt[:market_section_end] +
                multi_coin_section + "\n\n" +
                base_prompt[market_section_end:]
            )
        else:
            # Fallback: append at end
            enhanced_prompt = base_prompt.replace(
                "Respond ONLY with the JSON object, no additional text.",
                f"{multi_coin_section}\n\nRespond ONLY with the JSON object, no additional text."
            )
        
        logger.debug(f"Built enhanced prompt with multi-coin context for {symbol}")
        return enhanced_prompt