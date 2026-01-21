"""
Trinity Decision Block - Generates trading signals based on indicator confluence.

Framework: 200 SMA (regime) + 20 EMA (entry) + ADX (strength) + RSI (momentum) + Supertrend (exit) + Volume
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from decimal import Decimal

from ..core.logger import get_logger
from ..core.config import config
from ..models.signal import SignalType, TradingSignal, SignalSide
from .block_market_data import MarketSnapshot

logger = get_logger(__name__)


@dataclass
class TrinityDecision:
    """Result of Trinity decision analysis."""

    symbol: str
    should_enter: bool
    entry_side: Optional[SignalSide] = None
    confidence: float = 0.0  # 0-1
    reason: str = ""
    confluence_score: float = 0.0  # 0-100
    signals_met: int = 0  # How many conditions met


class TrinityDecisionBlock:
    """
    Generates trading signals based on indicator confluence (Trinity framework).

    Entry Logic:
    - Regime: Price > 200 SMA (uptrend)
    - Trend Strength: ADX > 25
    - Pullback: Price touched EMA_20 zone (dipped below)
    - Bounce: Price closed back above EMA_20
    - Momentum: RSI < 40 (oversold)
    - Volume: Current volume > volume MA
    - MACD: MACD line > signal line (momentum confirmation)
    - OBV: On-Balance Volume trending up (accumulation detected)

    Entry requires: At least 4/7 signals for entry, 5/7 for strong entry

    Exit Logic:
    - Supertrend turns red (below current price)
    - OR price breaks below 200 SMA (regime change)
    - OR RSI > 75 (extreme overbought)
    """

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    async def get_decisions(
        self,
        market_data: Dict[str, MarketSnapshot],
        portfolio_context: Dict[str, Any],
    ) -> Optional[Dict[str, TradingSignal]]:
        """
        Generate trading signals based on Trinity indicator confluence.

        Args:
            market_data: Dict of symbol -> MarketSnapshot (with Trinity indicators)
            portfolio_context: Portfolio state (cash, equity, positions)

        Returns:
            Dict of symbol -> TradingSignal, or None if no valid signals
        """
        signals = {}

        for symbol, snapshot in market_data.items():
            if not snapshot.signals:  # No Trinity indicators calculated
                continue

            # Analyze confluence for this symbol
            decision = self._analyze_confluence(symbol, snapshot)

            if decision.should_enter:
                # Calculate stop loss and take profit based on entry price
                entry_price = snapshot.price
                side = decision.entry_side or SignalSide.LONG

                sl_pct = Decimal(str(config.DEFAULT_STOP_LOSS_PCT))
                tp_pct = Decimal(str(config.DEFAULT_TAKE_PROFIT_PCT))

                if side == SignalSide.LONG:
                    stop_loss = entry_price * (Decimal("1") - sl_pct)
                    take_profit = entry_price * (Decimal("1") + tp_pct)
                else:  # SHORT
                    stop_loss = entry_price * (Decimal("1") + sl_pct)
                    take_profit = entry_price * (Decimal("1") - tp_pct)

                # Generate entry signal
                signal = TradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.BUY_TO_ENTER,
                    side=side,
                    confidence=decision.confidence,
                    reasoning=decision.reason,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    size_pct=self._calculate_position_size(decision.confidence),
                    leverage=1,
                )
                signals[symbol] = signal

                self.logger.info(
                    f"[TRINITY] {symbol}: BUY signal | Confluence: {decision.confluence_score:.0f}/100 | "
                    f"Signals: {decision.signals_met}/7 | Confidence: {decision.confidence:.0f}%"
                )
            else:
                self.logger.debug(
                    f"[TRINITY] {symbol}: No entry (confluence {decision.confluence_score:.0f}/100) | "
                    f"Signals: {decision.signals_met}/7"
                )

        return signals if signals else None

    def _analyze_confluence(self, symbol: str, snapshot: MarketSnapshot) -> TrinityDecision:
        """
        Analyze indicator confluence for entry signal.

        Returns TrinityDecision with should_enter and confidence.
        """
        signals = snapshot.signals or {}
        confluence = snapshot.confluence_score or 0.0

        # Check each condition
        regime_ok = signals.get("regime_filter", False)           # Price > 200 SMA
        trend_strength_ok = signals.get("trend_strength", False)  # ADX > 25
        pullback_detected = signals.get("pullback_detected", False)  # Price in EMA zone
        price_bounced = signals.get("price_bounced", False)       # Back above EMA
        oversold = signals.get("oversold", False)                 # RSI < 40
        volume_confirmed = signals.get("volume_confirmed", False) # Vol > SMA vol
        macd_positive = signals.get("macd_positive", False)       # MACD line > signal line
        obv_accumulating = signals.get("obv_accumulating", False) # OBV trending up
        bollinger_expansion = signals.get("bollinger_expansion", False) # BB expansion
        stoch_bullish_cross = signals.get("stoch_bullish_cross", False) # Stochastic K-D cross

        # Log debugging signals
        if macd_positive or signals.get("macd_bullish_cross", False):
            self.logger.debug(f"[TRINITY] {symbol}: MACD positive={macd_positive}, bullish_cross={signals.get('macd_bullish_cross', False)}")
        if obv_accumulating:
            self.logger.debug(f"[TRINITY] {symbol}: OBV accumulating={obv_accumulating}")
        if bollinger_expansion:
            self.logger.debug(f"[TRINITY] {symbol}: Bollinger expansion detected")
        if stoch_bullish_cross:
            self.logger.debug(f"[TRINITY] {symbol}: Stochastic bullish cross detected")

        # Count how many signals met (including MACD, OBV, Bollinger, and Stochastic)
        conditions = [regime_ok, trend_strength_ok, price_bounced, oversold, volume_confirmed, macd_positive, obv_accumulating]
        signals_met = sum(conditions)
        total_signals = 7

        # Add confluence boosts for secondary indicators
        if bollinger_expansion:
            confluence += 15
        if stoch_bullish_cross:
            confluence += 10

        # Decision logic: need strong confluence
        if signals_met >= 5:
            confidence = min(signals_met / total_signals, 1.0)
            reason = f"Strong confluence ({signals_met}/{total_signals} signals) | Confluence score: {confluence:.0f}/100"
            return TrinityDecision(
                symbol=symbol,
                should_enter=True,
                entry_side=SignalSide.LONG,
                confidence=confidence,
                reason=reason,
                confluence_score=confluence,
                signals_met=signals_met,
            )
        elif signals_met >= 4:
            confidence = signals_met / total_signals
            reason = f"Moderate confluence ({signals_met}/{total_signals} signals) | Confluence score: {confluence:.0f}/100"
            return TrinityDecision(
                symbol=symbol,
                should_enter=True,
                entry_side=SignalSide.LONG,
                confidence=confidence,
                reason=reason,
                confluence_score=confluence,
                signals_met=signals_met,
            )
        else:
            confidence = signals_met / total_signals
            reason = f"Weak confluence ({signals_met}/{total_signals} signals) - waiting for more confirmation"
            return TrinityDecision(
                symbol=symbol,
                should_enter=False,
                confidence=confidence,
                reason=reason,
                confluence_score=confluence,
                signals_met=signals_met,
            )

    def should_exit(self, symbol: str, snapshot: MarketSnapshot) -> tuple[bool, str]:
        """
        Check if position should be exited based on Trinity indicators.

        Returns: (should_exit, reason)
        """
        supertrend_signal = snapshot.supertrend_signal or "neutral"
        rsi = snapshot.signals.get("rsi", 50) if snapshot.signals else 50
        price = float(snapshot.price)
        sma_200 = snapshot.sma_200

        # Exit condition 1: Supertrend turned red
        if supertrend_signal == "sell":
            return True, "Supertrend turned red (trailing stop hit)"

        # Exit condition 2: Price broke below 200 SMA (regime change)
        if sma_200 and price < sma_200:
            return True, f"Price broke below 200 SMA (${sma_200:.2f}) - regime change"

        # Exit condition 3: RSI extreme overbought
        if rsi > 75:
            return True, f"RSI extreme overbought ({rsi:.0f}%) - take profit"

        return False, "Position still valid"

    def _calculate_position_size(self, confidence: float) -> float:
        """
        Calculate position size based on signal confidence.

        - Low confidence (0.4-0.6): 1% of capital
        - Medium confidence (0.6-0.8): 2% of capital
        - High confidence (0.8+): 3% of capital
        """
        if confidence < 0.6:
            return 0.01
        elif confidence < 0.8:
            return 0.02
        else:
            return 0.03
