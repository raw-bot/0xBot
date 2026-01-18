"""
Technical Indicators Block - Implements the "Trinity" Framework
Calculates: 200 SMA (Daily), 20 EMA (1H), ADX, RSI, Supertrend, Volume
No external dependencies (no pandas_ta) - pure calculations
"""

import pandas as pd
from typing import Optional, Dict, Any
from decimal import Decimal
import math

from ..core.logger import get_logger

logger = get_logger(__name__)


class IndicatorBlock:
    """
    Calculates technical indicators using the framework:
    - Trend: 200 SMA (daily), 20 EMA (1H)
    - Filter: ADX (1H) - prevents chop
    - Momentum: RSI (1H)
    - Risk/Exit: Supertrend (1H)
    - Confirmation: Volume
    """

    def __init__(self):
        self.logger = get_logger(__name__)

    # ============ INDICATOR CALCULATIONS ============

    def sma(self, values: list, period: int) -> list:
        """Simple Moving Average"""
        if len(values) < period:
            return [None] * len(values)
        result = [None] * (period - 1)
        for i in range(period - 1, len(values)):
            result.append(sum(values[i - period + 1:i + 1]) / period)
        return result

    def ema(self, values: list, period: int) -> list:
        """Exponential Moving Average"""
        if len(values) < period:
            return [None] * len(values)

        result = [None] * (period - 1)
        sma_val = sum(values[:period]) / period
        result.append(sma_val)

        multiplier = 2 / (period + 1)
        for i in range(period, len(values)):
            ema_val = values[i] * multiplier + result[-1] * (1 - multiplier)
            result.append(ema_val)

        return result

    def rsi(self, values: list, period: int = 14) -> list:
        """Relative Strength Index"""
        if len(values) < period + 1:
            return [None] * len(values)

        result = [None] * period

        gains = []
        losses = []

        for i in range(1, len(values)):
            change = values[i] - values[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        if avg_loss == 0:
            result.append(100)
        else:
            rs = avg_gain / avg_loss
            result.append(100 - (100 / (1 + rs)))

        for i in range(period + 1, len(values)):
            avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period

            if avg_loss == 0:
                result.append(100)
            else:
                rs = avg_gain / avg_loss
                result.append(100 - (100 / (1 + rs)))

        return result

    def atr(self, highs: list, lows: list, closes: list, period: int = 14) -> list:
        """Average True Range"""
        if len(highs) < period:
            return [None] * len(highs)

        tr_values = []
        for i in range(len(highs)):
            if i == 0:
                tr = highs[i] - lows[i]
            else:
                tr = max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i - 1]),
                    abs(lows[i] - closes[i - 1])
                )
            tr_values.append(tr)

        result = [None] * (period - 1)
        atr_val = sum(tr_values[:period]) / period
        result.append(atr_val)

        for i in range(period, len(tr_values)):
            atr_val = (atr_val * (period - 1) + tr_values[i]) / period
            result.append(atr_val)

        return result

    def supertrend(self, highs: list, lows: list, closes: list, period: int = 10, multiplier: float = 3.0) -> tuple[list, list]:
        """
        Supertrend indicator
        Returns: (supertrend_values, trend_signals)
        """
        if len(highs) < period:
            return [None] * len(highs), ["neutral"] * len(highs)

        hl2 = [(highs[i] + lows[i]) / 2 for i in range(len(highs))]
        atr_vals = self.atr(highs, lows, closes, period)

        basic_ub = [hl2[i] + multiplier * atr_vals[i] if atr_vals[i] is not None else None for i in range(len(hl2))]
        basic_lb = [hl2[i] - multiplier * atr_vals[i] if atr_vals[i] is not None else None for i in range(len(hl2))]

        final_ub = [None] * len(highs)
        final_lb = [None] * len(highs)
        supertrend = [None] * len(highs)
        trend = ["neutral"] * len(highs)

        for i in range(len(highs)):
            if i == 0:
                if basic_ub[i] is not None and basic_lb[i] is not None:
                    final_ub[i] = basic_ub[i]
                    final_lb[i] = basic_lb[i]
            else:
                if basic_ub[i] is not None and basic_lb[i] is not None and final_ub[i - 1] is not None and final_lb[i - 1] is not None:
                    final_ub[i] = basic_ub[i] if basic_ub[i] < final_ub[i - 1] or closes[i - 1] > final_ub[i - 1] else final_ub[i - 1]
                    final_lb[i] = basic_lb[i] if basic_lb[i] > final_lb[i - 1] or closes[i - 1] < final_lb[i - 1] else final_lb[i - 1]
                elif basic_ub[i] is not None and basic_lb[i] is not None:
                    final_ub[i] = basic_ub[i]
                    final_lb[i] = basic_lb[i]

        for i in range(len(highs)):
            if i == 0:
                if final_ub[i] is not None:
                    if closes[i] <= final_ub[i]:
                        supertrend[i] = final_ub[i]
                        trend[i] = "sell"
                    else:
                        supertrend[i] = final_lb[i]
                        trend[i] = "buy"
            else:
                if supertrend[i - 1] is None:
                    if final_ub[i] is not None and closes[i] <= final_ub[i]:
                        supertrend[i] = final_ub[i]
                        trend[i] = "sell"
                    elif final_lb[i] is not None:
                        supertrend[i] = final_lb[i]
                        trend[i] = "buy"
                else:
                    if closes[i] <= supertrend[i - 1] and final_ub[i] is not None:
                        supertrend[i] = final_ub[i]
                        trend[i] = "sell"
                    elif final_lb[i] is not None:
                        supertrend[i] = final_lb[i]
                        trend[i] = "buy"

        return supertrend, trend

    # ============ DATA CONVERSION & PROCESSING ============

    def convert_ccxt_to_dict(self, ohlcv_list: list) -> Dict[str, list]:
        """
        Convert CCXT OHLCV format to dict of lists.

        CCXT format: [[timestamp, open, high, low, close, volume], ...]

        Returns:
            Dict with keys: ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        """
        if not ohlcv_list or len(ohlcv_list) == 0:
            return {}

        timestamps = [candle[0] for candle in ohlcv_list]
        opens = [float(candle[1]) for candle in ohlcv_list]
        highs = [float(candle[2]) for candle in ohlcv_list]
        lows = [float(candle[3]) for candle in ohlcv_list]
        closes = [float(candle[4]) for candle in ohlcv_list]
        volumes = [float(candle[5]) for candle in ohlcv_list]

        return {
            'timestamp': timestamps,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        }

    def calculate_indicators_from_ccxt(
        self,
        ohlcv_dict: Dict[str, list]
    ) -> Dict[str, Any]:
        """
        Calculate indicators from CCXT OHLCV data.

        Args:
            ohlcv_dict: Dict with keys ['timestamp', 'open', 'high', 'low', 'close', 'volume']

        Returns:
            Dict of indicator results
        """
        if not ohlcv_dict or len(ohlcv_dict.get('close', [])) < 200:
            return {}

        closes = ohlcv_dict['close']
        highs = ohlcv_dict['high']
        lows = ohlcv_dict['low']
        volumes = ohlcv_dict['volume']

        # === TREND INDICATORS ===
        sma_200_vals = self.sma(closes, 200)
        sma_200 = sma_200_vals[-1] if sma_200_vals[-1] is not None else None

        ema_20_vals = self.ema(closes, 20)
        ema_20 = ema_20_vals[-1] if ema_20_vals[-1] is not None else None

        # === MOMENTUM INDICATORS ===
        rsi_vals = self.rsi(closes, 14)
        rsi_val = rsi_vals[-1] if rsi_vals[-1] is not None else 50

        # === VOLATILITY & EXIT ===
        atr_vals = self.atr(highs, lows, closes, 14)
        atr_val = atr_vals[-1] if atr_vals[-1] is not None else 0

        supertrend_vals, supertrend_trends = self.supertrend(highs, lows, closes, 10, 3.0)
        supertrend = supertrend_vals[-1] if supertrend_vals[-1] is not None else None
        supertrend_signal = supertrend_trends[-1] if supertrend_trends[-1] else "neutral"

        # === VOLUME ===
        volume_sma = self.sma(volumes, 20)
        volume_ma = volume_sma[-1] if volume_sma[-1] is not None else 0
        current_volume = volumes[-1]

        # === CURRENT PRICE ===
        current_price = closes[-1]

        # === ADX (simplified - using trend strength based on slope) ===
        # For simplicity, we'll use the rate of change of 200 SMA as trend strength
        if len(sma_200_vals) >= 3 and sma_200_vals[-3] is not None:
            sma_slope = (sma_200 - sma_200_vals[-3]) / sma_200_vals[-3] * 100  # percent change
            adx = min(max(abs(sma_slope) * 2, 0), 100)  # Scale to 0-100
        else:
            adx = 0

        # === SIGNAL GENERATION ===
        regime_ok = current_price > sma_200 if sma_200 else False
        trend_strength_ok = adx > 25

        if ema_20:
            zone_upper = ema_20 * 1.005
            zone_lower = ema_20 * 0.995
            pullback_detected = (lows[-1] <= zone_lower)
        else:
            pullback_detected = False

        price_above_ema = current_price > ema_20 if ema_20 else False
        oversold = rsi_val < 40
        volume_confirmed = current_volume > volume_ma

        confluence_signals = [
            regime_ok,
            trend_strength_ok,
            pullback_detected,
            oversold,
            volume_confirmed,
        ]
        confluence_score = sum(confluence_signals) * 20

        return {
            'sma_200': sma_200,
            'ema_20': ema_20,
            'adx': adx,
            'rsi': rsi_val,
            'atr': atr_val,
            'supertrend': supertrend,
            'supertrend_signal': supertrend_signal,
            'volume_ma': volume_ma,
            'current_volume': current_volume,
            'price': current_price,
            'confluence_score': confluence_score,
            'signals': {
                'regime_filter': regime_ok,
                'trend_strength': trend_strength_ok,
                'pullback_detected': pullback_detected,
                'price_bounced': price_above_ema,
                'oversold': oversold,
                'volume_confirmed': volume_confirmed
            }
        }

    def get_entry_signal(self, indicator_data: Dict[str, Any]) -> tuple[bool, str, float]:
        """
        Determine if entry conditions are met based on indicator confluence.

        Returns:
            (should_enter: bool, reason: str, confidence: float 0-1)
        """
        signals = indicator_data.get('signals', {})
        confluence = indicator_data.get('confluence_score', 0)

        required_signals = [
            signals.get('regime_filter', False),
            signals.get('trend_strength', False),
            signals.get('price_bounced', False),
            signals.get('oversold', False),
            signals.get('volume_confirmed', False),
        ]

        met = sum(required_signals)

        if met >= 4:
            confidence = min(met / 5, 1.0)
            reason = f"Strong confluence ({met}/5 signals + {confluence}/100 score)"
            return True, reason, confidence
        elif met == 3:
            confidence = met / 5
            reason = f"Moderate confluence ({met}/5 signals)"
            return True, reason, confidence
        else:
            confidence = met / 5
            reason = f"Weak confluence ({met}/5 signals) - waiting"
            return False, reason, confidence

    def get_exit_signal(self, indicator_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Determine if exit conditions are met.

        Returns:
            (should_exit: bool, reason: str)
        """
        supertrend_signal = indicator_data.get('supertrend_signal', 'neutral')
        rsi = indicator_data.get('rsi', 50)
        price = indicator_data.get('price', 0)
        sma_200 = indicator_data.get('sma_200', 0)

        if supertrend_signal == "sell":
            return True, "Supertrend turned red - stop loss hit"

        if price < sma_200:
            return True, "Price broke below 200 SMA - regime change"

        if rsi > 75:
            return True, "RSI extreme overbought (>75) - take profit"

        return False, "Position still valid"
