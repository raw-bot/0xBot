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
        price_above_vwap_upper = signals.get("price_above_vwap_upper", False) # VWAP breakout

        # Ichimoku signals (market structure understanding)
        price_above_kumo = signals.get("price_above_kumo", False) # Price above cloud (bullish structure)
        tenkan_above_kijun = signals.get("tenkan_above_kijun", False) # Bullish line structure
        cloud_bullish_cross = signals.get("cloud_bullish_cross", False) # Price crossing above cloud
        kumo_bullish = signals.get("kumo_bullish", False) # Cloud bullish orientation

        # Order Flow Imbalance signals (microstructure analysis)
        delta_positive = signals.get("delta_positive", False) # Cumulative delta > 0 (buyers in control)
        delta_surge = signals.get("delta_surge", False) # Extreme volume imbalance
        delta_bullish_cross = signals.get("delta_bullish_cross", False) # Delta crosses above 0
        delta_divergence = signals.get("delta_divergence", False) # Delta strength during consolidation

        # Log debugging signals
        if macd_positive or signals.get("macd_bullish_cross", False):
            self.logger.debug(f"[TRINITY] {symbol}: MACD positive={macd_positive}, bullish_cross={signals.get('macd_bullish_cross', False)}")
        if obv_accumulating:
            self.logger.debug(f"[TRINITY] {symbol}: OBV accumulating={obv_accumulating}")
        if bollinger_expansion:
            self.logger.debug(f"[TRINITY] {symbol}: Bollinger expansion detected")
        if stoch_bullish_cross:
            self.logger.debug(f"[TRINITY] {symbol}: Stochastic bullish cross detected")
        if price_above_vwap_upper:
            self.logger.debug(f"[TRINITY] {symbol}: Price above VWAP upper band detected")
        if price_above_kumo or cloud_bullish_cross:
            self.logger.debug(f"[TRINITY] {symbol}: Ichimoku - Price above cloud={price_above_kumo}, Cloud cross={cloud_bullish_cross}, Tenkan>Kijun={tenkan_above_kijun}")
        if delta_positive or delta_surge or delta_bullish_cross:
            self.logger.debug(f"[TRINITY] {symbol}: OFI - Positive={delta_positive}, Surge={delta_surge}, Bullish Cross={delta_bullish_cross}, Divergence={delta_divergence}")

        # Count how many signals met (including MACD, OBV, Bollinger, Stochastic, and VWAP)
        conditions = [regime_ok, trend_strength_ok, price_bounced, oversold, volume_confirmed, macd_positive, obv_accumulating]
        signals_met = sum(conditions)
        total_signals = 7

        # === WEIGHTED CONFLUENCE SYSTEM ===
        # Define weights for each signal category
        weight_regime = 0.25        # 25% - Most important (regime filter)
        weight_trend = 0.20         # 20% - Trend confirmation
        weight_entry = 0.20         # 20% - Entry quality (pullback + bounce)
        weight_momentum = 0.20      # 20% - Momentum strength (oversold + MACD + OBV)
        weight_volume = 0.10        # 10% - Volume confirmation
        weight_volatility = 0.05    # 5% - Volatility readiness (Bollinger + Stochastic)

        # Map signals to weighted categories (1 = signal met, 0 = signal not met)
        # Ichimoku signals enhance regime confirmation (price above cloud + bullish structure)
        ichimoku_regime_bonus = (price_above_kumo and tenkan_above_kijun and kumo_bullish)
        regime_score = 1 if (regime_ok or ichimoku_regime_bonus) else 0

        # Ichimoku structure can confirm trend
        ichimoku_trend_signal = (price_above_kumo or tenkan_above_kijun)
        trend_score = 1 if (trend_strength_ok or ichimoku_trend_signal) else 0

        entry_score = 1 if (pullback_detected and price_bounced) else 0  # Both pullback AND bounce
        # Ichimoku cloud crossing is a strong entry signal
        if cloud_bullish_cross:
            entry_score = 1

        momentum_score = 1 if (oversold or macd_positive or obv_accumulating or delta_positive or delta_bullish_cross) else 0  # Any momentum signal
        volume_score = 1 if (volume_confirmed or delta_surge) else 0  # Volume or delta surge
        volatility_score = 1 if (bollinger_expansion or stoch_bullish_cross or price_above_vwap_upper or cloud_bullish_cross or delta_divergence) else 0  # Any volatility signal

        # Calculate weighted confluence (0-1 scale)
        weighted_confluence = (
            (regime_score * weight_regime) +
            (trend_score * weight_trend) +
            (entry_score * weight_entry) +
            (momentum_score * weight_momentum) +
            (volume_score * weight_volume) +
            (volatility_score * weight_volatility)
        )

        # Convert to 0-100 scale for consistency
        weighted_confluence_pct = weighted_confluence * 100

        # Add secondary confluence boosts (these further reinforce the weighted score)
        if bollinger_expansion:
            confluence += 15
        if stoch_bullish_cross:
            confluence += 10
        if price_above_vwap_upper:
            confluence += 12
        # Ichimoku boosts (per PRD specifications)
        if price_above_kumo:
            confluence += 20  # Strong bullish structure
        if cloud_bullish_cross:
            confluence += 25  # Strong trend confirmation via cloud crossing
        if tenkan_above_kijun and kumo_bullish:
            confluence += 15  # Bullish line structure + orientation
        # Order Flow Imbalance boosts (per PRD specifications)
        if delta_bullish_cross:
            confluence += 18  # Institutional buying reversal
        if delta_surge:
            confluence += 12  # Extreme volume imbalance
        if delta_divergence:
            confluence += 10  # Strength during consolidation

        # Decision logic: weighted threshold
        # Old system required 5/7 signals (71%), new system uses weighted confidence
        # 95%+ = very strong (all major + some minor signals)
        # 80%+ = strong (major signals met)
        # 65%+ = moderate (some key signals met)
        # 50%+ = weak (minimal signals met)
        # <50% = no entry

        if weighted_confluence >= 0.95:
            confidence = min(weighted_confluence, 1.0)
            reason = f"Very strong confluence ({signals_met}/{total_signals} signals, {weighted_confluence_pct:.0f}% weighted)"
            return TrinityDecision(
                symbol=symbol,
                should_enter=True,
                entry_side=SignalSide.LONG,
                confidence=confidence,
                reason=reason,
                confluence_score=confluence,
                signals_met=signals_met,
            )
        elif weighted_confluence >= 0.80:
            confidence = weighted_confluence
            reason = f"Strong confluence ({signals_met}/{total_signals} signals, {weighted_confluence_pct:.0f}% weighted)"
            return TrinityDecision(
                symbol=symbol,
                should_enter=True,
                entry_side=SignalSide.LONG,
                confidence=confidence,
                reason=reason,
                confluence_score=confluence,
                signals_met=signals_met,
            )
        elif weighted_confluence >= 0.65:
            confidence = weighted_confluence
            reason = f"Moderate confluence ({signals_met}/{total_signals} signals, {weighted_confluence_pct:.0f}% weighted)"
            return TrinityDecision(
                symbol=symbol,
                should_enter=True,
                entry_side=SignalSide.LONG,
                confidence=confidence,
                reason=reason,
                confluence_score=confluence,
                signals_met=signals_met,
            )
        elif weighted_confluence >= 0.50:
            confidence = weighted_confluence
            reason = f"Weak confluence ({signals_met}/{total_signals} signals, {weighted_confluence_pct:.0f}% weighted) - marginal entry"
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
            confidence = weighted_confluence
            reason = f"Insufficient confluence ({weighted_confluence_pct:.0f}% weighted) - waiting for more signals"
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
        Calculate adaptive position size based on weighted confidence (0-1 scale).

        Weighted Confluence Position Sizing:
        - 95%+ confidence: 10% of capital (very strong setup)
        - 80-95% confidence: 8% of capital (strong setup)
        - 65-80% confidence: 6% of capital (moderate setup)
        - 50-65% confidence: 4% of capital (weak setup)
        - <50% confidence: 0% (no entry)

        This adaptive sizing ensures better risk management and Kelly-compatible position allocation.
        """
        if confidence >= 0.95:
            return 0.10
        elif confidence >= 0.80:
            return 0.08
        elif confidence >= 0.65:
            return 0.06
        elif confidence >= 0.50:
            return 0.04
        else:
            return 0.00
