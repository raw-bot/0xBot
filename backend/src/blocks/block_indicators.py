"""
Technical Indicators Block - Implements the "Trinity" Framework
Calculates: 200 SMA (Daily), 20 EMA (1H), ADX, RSI, Supertrend, Volume
No external dependencies (no pandas_ta) - pure calculations
"""

import pandas as pd  # type: ignore[import-untyped]
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

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    # ============ INDICATOR CALCULATIONS ============

    def sma(self, values: list[float], period: int) -> list[float | None]:
        """Simple Moving Average"""
        if len(values) < period:
            return [None] * len(values)
        result: list[float | None] = [None] * (period - 1)
        for i in range(period - 1, len(values)):
            result.append(sum(values[i - period + 1:i + 1]) / period)
        return result

    def ema(self, values: list[float], period: int) -> list[float | None]:
        """Exponential Moving Average"""
        if len(values) < period:
            return [None] * len(values)

        result: list[float | None] = [None] * (period - 1)
        sma_val = sum(values[:period]) / period
        result.append(sma_val)

        multiplier = 2 / (period + 1)
        for i in range(period, len(values)):
            last_val = result[-1]
            if last_val is not None:
                ema_val = values[i] * multiplier + last_val * (1 - multiplier)
                result.append(ema_val)

        return result

    def rsi(self, values: list[float], period: int = 14) -> list[float | None]:
        """Relative Strength Index"""
        if len(values) < period + 1:
            return [None] * len(values)

        result: list[float | None] = [None] * period

        gains: list[float] = []
        losses: list[float] = []

        for i in range(1, len(values)):
            change = values[i] - values[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(change))

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100 - (100 / (1 + rs)))

        for i in range(period + 1, len(values)):
            avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period

            if avg_loss == 0:
                result.append(100.0)
            else:
                rs = avg_gain / avg_loss
                result.append(100 - (100 / (1 + rs)))

        return result

    def atr(self, highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[float | None]:
        """Average True Range"""
        if len(highs) < period:
            return [None] * len(highs)

        tr_values: list[float] = []
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

        result: list[float | None] = [None] * (period - 1)
        atr_val = sum(tr_values[:period]) / period
        result.append(atr_val)

        for i in range(period, len(tr_values)):
            atr_val = (atr_val * (period - 1) + tr_values[i]) / period
            result.append(atr_val)

        return result

    def calculate_vwap(self, highs: list[float], lows: list[float], closes: list[float], volumes: list[float]) -> float | None:
        """
        Calculate Volume Weighted Average Price.

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            volumes: List of volumes

        Returns:
            Current VWAP value or None if insufficient data
        """
        if not highs or not lows or not closes or not volumes or len(closes) < 1:
            return None

        cumulative_tp_volume = 0.0
        cumulative_volume = 0.0

        for i in range(len(closes)):
            # Typical Price = (High + Low + Close) / 3
            tp = (highs[i] + lows[i] + closes[i]) / 3.0
            vol = volumes[i]

            cumulative_tp_volume += tp * vol
            cumulative_volume += vol

        if cumulative_volume == 0:
            return None

        return cumulative_tp_volume / cumulative_volume

    def supertrend(self, highs: list[float], lows: list[float], closes: list[float], period: int = 10, multiplier: float = 3.0) -> tuple[list[float | None], list[str]]:
        """
        Supertrend indicator
        Returns: (supertrend_values, trend_signals)
        """
        if len(highs) < period:
            return [None] * len(highs), ["neutral"] * len(highs)

        hl2: list[float] = [(highs[i] + lows[i]) / 2 for i in range(len(highs))]
        atr_vals = self.atr(highs, lows, closes, period)

        basic_ub: list[float | None] = []
        basic_lb: list[float | None] = []
        for i in range(len(hl2)):
            atr_val = atr_vals[i]
            if atr_val is not None:
                basic_ub.append(hl2[i] + multiplier * atr_val)
                basic_lb.append(hl2[i] - multiplier * atr_val)
            else:
                basic_ub.append(None)
                basic_lb.append(None)

        final_ub: list[float | None] = [None] * len(highs)
        final_lb: list[float | None] = [None] * len(highs)
        supertrend: list[float | None] = [None] * len(highs)
        trend: list[str] = ["neutral"] * len(highs)

        for i in range(len(highs)):
            if i == 0:
                ub = basic_ub[i]
                lb = basic_lb[i]
                if ub is not None and lb is not None:
                    final_ub[i] = ub
                    final_lb[i] = lb
            else:
                ub = basic_ub[i]
                lb = basic_lb[i]
                ub_prev = final_ub[i - 1]
                lb_prev = final_lb[i - 1]
                if ub is not None and lb is not None and ub_prev is not None and lb_prev is not None:
                    final_ub[i] = ub if ub < ub_prev or closes[i - 1] > ub_prev else ub_prev
                    final_lb[i] = lb if lb > lb_prev or closes[i - 1] < lb_prev else lb_prev
                elif ub is not None and lb is not None:
                    final_ub[i] = ub
                    final_lb[i] = lb

        for i in range(len(highs)):
            if i == 0:
                ub = final_ub[i]
                lb = final_lb[i]
                if ub is not None:
                    if closes[i] <= ub:
                        supertrend[i] = ub
                        trend[i] = "sell"
                    else:
                        supertrend[i] = lb
                        trend[i] = "buy"
            else:
                st_prev = supertrend[i - 1]
                if st_prev is None:
                    ub = final_ub[i]
                    lb = final_lb[i]
                    if ub is not None and closes[i] <= ub:
                        supertrend[i] = ub
                        trend[i] = "sell"
                    elif lb is not None:
                        supertrend[i] = lb
                        trend[i] = "buy"
                else:
                    ub = final_ub[i]
                    lb = final_lb[i]
                    if closes[i] <= st_prev and ub is not None:
                        supertrend[i] = ub
                        trend[i] = "sell"
                    elif lb is not None:
                        supertrend[i] = lb
                        trend[i] = "buy"

        return supertrend, trend

    # ============ DATA CONVERSION & PROCESSING ============

    def convert_ccxt_to_dict(self, ohlcv_list: list[Any]) -> dict[str, list[Any]]:
        """
        Convert CCXT OHLCV format to dict of lists.

        CCXT format: [[timestamp, open, high, low, close, volume], ...]

        Returns:
            Dict with keys: ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        """
        if not ohlcv_list or len(ohlcv_list) == 0:
            return {}

        timestamps: list[Any] = [candle[0] for candle in ohlcv_list]
        opens: list[float] = [float(candle[1]) for candle in ohlcv_list]
        highs: list[float] = [float(candle[2]) for candle in ohlcv_list]
        lows: list[float] = [float(candle[3]) for candle in ohlcv_list]
        closes: list[float] = [float(candle[4]) for candle in ohlcv_list]
        volumes: list[float] = [float(candle[5]) for candle in ohlcv_list]

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
        ohlcv_dict: dict[str, list[Any]]
    ) -> dict[str, Any]:
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

        # === VWAP (Volume Weighted Average Price) ===
        vwap = self.calculate_vwap(highs, lows, closes, volumes)

        # === TRUE ADX (Average Directional Index) ===
        # ADX > 25: Strong trend, 15-25: Weak trend, < 15: Choppy
        from ..services.indicator_service import IndicatorService
        adx_val = IndicatorService.calculate_adx(highs, lows, closes, 14)
        adx = adx_val if adx_val is not None else 0

        # === MACD (Moving Average Convergence Divergence) ===
        macd_data = IndicatorService.calculate_macd(closes, fast_period=12, slow_period=26, signal_period=9)
        macd_line = macd_data['macd'][-1] if macd_data['macd'] and macd_data['macd'][-1] is not None else 0
        macd_signal = macd_data['signal'][-1] if macd_data['signal'] and macd_data['signal'][-1] is not None else 0
        macd_histogram = macd_data['histogram'][-1] if macd_data['histogram'] and macd_data['histogram'][-1] is not None else 0
        # Check for bullish cross: MACD line crosses above signal line
        macd_prev = macd_data['macd'][-2] if len(macd_data['macd']) > 1 and macd_data['macd'][-2] is not None else None
        signal_prev = macd_data['signal'][-2] if len(macd_data['signal']) > 1 and macd_data['signal'][-2] is not None else None
        macd_bullish_cross = (macd_prev is not None and signal_prev is not None and
                             macd_prev <= signal_prev and macd_line > macd_signal)

        # === OBV (On-Balance Volume) - Accumulation/Distribution ===
        current_obv, obv_ma, obv_trending = IndicatorService.calculate_obv(closes, volumes, obv_ma_period=14)
        logger.debug(f"[OBV] Current: {current_obv:.0f}, MA: {obv_ma:.0f}, Accumulating: {obv_trending}")

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

        # VWAP signal
        price_above_vwap = current_price > vwap if vwap else False
        if vwap:
            logger.debug(f"[VWAP] Price: ${current_price:.2f}, VWAP: ${vwap:.2f}, Signal: {price_above_vwap}")

        # ADX signal
        adx_strong = adx > 25
        adx_weak = 15 < adx <= 25
        adx_choppy = adx <= 15
        logger.debug(f"[ADX] Value: {adx:.1f}, Strong: {adx_strong}, Weak: {adx_weak}, Choppy: {adx_choppy}")

        # MACD signal
        macd_positive = macd_line > macd_signal
        logger.debug(f"[MACD] Line: {macd_line:.6f}, Signal: {macd_signal:.6f}, Positive: {macd_positive}, Cross: {macd_bullish_cross}")

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
            'vwap': vwap,
            'macd_line': macd_line,
            'macd_signal': macd_signal,
            'macd_histogram': macd_histogram,
            'obv': current_obv,
            'obv_ma': obv_ma,
            'confluence_score': confluence_score,
            'signals': {
                'regime_filter': regime_ok,
                'trend_strength': trend_strength_ok,
                'pullback_detected': pullback_detected,
                'price_bounced': price_above_ema,
                'oversold': oversold,
                'volume_confirmed': volume_confirmed,
                'price_above_vwap': price_above_vwap,
                'macd_positive': macd_positive,
                'macd_bullish_cross': macd_bullish_cross,
                'obv_accumulating': obv_trending
            }
        }

    def get_entry_signal(self, indicator_data: dict[str, Any]) -> tuple[bool, str, float]:
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

    def get_exit_signal(self, indicator_data: dict[str, Any]) -> tuple[bool, str]:
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
