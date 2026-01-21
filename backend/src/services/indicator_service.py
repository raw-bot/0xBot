"""Technical indicator service using TA-Lib with caching support."""

from typing import Any, Optional

import numpy as np
import talib

from ..core.logger import get_logger

logger = get_logger(__name__)


def _to_array(data: list[float]) -> np.ndarray:
    """Convert list to numpy array."""
    return np.array(data, dtype=float)


def _clean_result(arr: np.ndarray) -> list[Optional[float]]:
    """Convert numpy array to list, replacing NaN with None."""
    return [float(val) if not np.isnan(val) else None for val in arr]


class IndicatorService:
    """Service for calculating technical indicators."""

    @staticmethod
    def calculate_ema(prices: list[float], period: int = 20) -> list[Optional[float]]:
        """Calculate Exponential Moving Average."""
        return _clean_result(talib.EMA(_to_array(prices), timeperiod=period))

    @staticmethod
    def calculate_sma(prices: list[float], period: int = 20) -> list[Optional[float]]:
        """Calculate Simple Moving Average."""
        return _clean_result(talib.SMA(_to_array(prices), timeperiod=period))

    @staticmethod
    def calculate_rsi(prices: list[float], period: int = 14) -> list[Optional[float]]:
        """Calculate Relative Strength Index (0-100 range)."""
        return _clean_result(talib.RSI(_to_array(prices), timeperiod=period))

    @staticmethod
    def calculate_macd(
        prices: list[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> dict[str, list[Optional[float]]]:
        """Calculate MACD. Returns dict with 'macd', 'signal', 'histogram' lists."""
        macd, signal, histogram = talib.MACD(
            _to_array(prices),
            fastperiod=fast_period,
            slowperiod=slow_period,
            signalperiod=signal_period,
        )
        return {
            "macd": _clean_result(macd),
            "signal": _clean_result(signal),
            "histogram": _clean_result(histogram),
        }

    @staticmethod
    def calculate_bollinger_bands(
        prices: list[float], period: int = 20, std_dev: int = 2
    ) -> dict[str, list[Optional[float | bool]]]:
        """Calculate Bollinger Bands with squeeze detection.

        Returns dict with:
        - 'upper', 'middle', 'lower': Band values
        - 'bandwidth': (upper - lower) / middle for each candle
        - 'squeeze': True if bandwidth < median_bandwidth * 0.7
        - 'expansion': True if bandwidth > median_bandwidth * 1.3
        - 'price_near_band': True if abs(price - middle) / (upper - lower) > 0.8
        """
        upper, middle, lower = talib.BBANDS(
            _to_array(prices), timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev
        )

        upper_clean = _clean_result(upper)
        middle_clean = _clean_result(middle)
        lower_clean = _clean_result(lower)

        # Calculate bandwidth: (upper - lower) / middle
        bandwidth: list[Optional[float]] = []
        for i in range(len(prices)):
            if upper_clean[i] is not None and middle_clean[i] is not None and lower_clean[i] is not None:
                if middle_clean[i] != 0:
                    bw = (upper_clean[i] - lower_clean[i]) / middle_clean[i]
                    bandwidth.append(bw)
                else:
                    bandwidth.append(None)
            else:
                bandwidth.append(None)

        # Calculate median bandwidth for squeeze detection
        valid_bandwidths = [bw for bw in bandwidth if bw is not None]
        median_bandwidth = None
        if valid_bandwidths:
            sorted_bw = sorted(valid_bandwidths)
            median_idx = len(sorted_bw) // 2
            median_bandwidth = sorted_bw[median_idx]

        # Detect squeeze and expansion
        squeeze_signals: list[Optional[bool]] = []
        expansion_signals: list[Optional[bool]] = []
        near_band_signals: list[Optional[bool]] = []

        for i in range(len(prices)):
            if bandwidth[i] is not None and median_bandwidth is not None:
                squeeze = bandwidth[i] < median_bandwidth * 0.7
                expansion = bandwidth[i] > median_bandwidth * 1.3
                squeeze_signals.append(squeeze)
                expansion_signals.append(expansion)

                # Check if price is near the band
                if upper_clean[i] is not None and lower_clean[i] is not None and middle_clean[i] is not None:
                    band_width = upper_clean[i] - lower_clean[i]
                    if band_width != 0:
                        price_distance = abs(prices[i] - middle_clean[i]) / band_width
                        near_band_signals.append(price_distance > 0.8)
                    else:
                        near_band_signals.append(False)
                else:
                    near_band_signals.append(False)
            else:
                squeeze_signals.append(None)
                expansion_signals.append(None)
                near_band_signals.append(None)

        return {
            "upper": upper_clean,
            "middle": middle_clean,
            "lower": lower_clean,
            "bandwidth": bandwidth,
            "squeeze": squeeze_signals,
            "expansion": expansion_signals,
            "price_near_band": near_band_signals,
        }

    @staticmethod
    def calculate_atr(
        highs: list[float], lows: list[float], closes: list[float], period: int = 14
    ) -> list[Optional[float]]:
        """Calculate Average True Range (volatility indicator)."""
        atr = talib.ATR(_to_array(highs), _to_array(lows), _to_array(closes), timeperiod=period)
        return _clean_result(atr)

    @staticmethod
    def calculate_stochastic(
        highs: list[float],
        lows: list[float],
        closes: list[float],
        fastk_period: int = 14,
        slowk_period: int = 3,
        slowd_period: int = 3,
    ) -> dict[str, list[Optional[float]]]:
        """Calculate Stochastic Oscillator. Returns dict with 'k' and 'd' lists."""
        slowk, slowd = talib.STOCH(
            _to_array(highs),
            _to_array(lows),
            _to_array(closes),
            fastk_period=fastk_period,
            slowk_period=slowk_period,
            slowd_period=slowd_period,
        )
        return {"k": _clean_result(slowk), "d": _clean_result(slowd)}

    @staticmethod
    def calculate_vwap(candles: list[dict[str, float]]) -> Optional[float]:
        """Calculate Volume Weighted Average Price.

        Args:
            candles: List of dicts with 'high', 'low', 'close', 'volume' keys

        Returns:
            Current VWAP value or None if insufficient data
        """
        if not candles or len(candles) < 1:
            return None

        cumulative_tp_volume = 0.0
        cumulative_volume = 0.0

        for candle in candles:
            high = float(candle.get("high", 0))
            low = float(candle.get("low", 0))
            close = float(candle.get("close", 0))
            volume = float(candle.get("volume", 0))

            # Typical Price = (High + Low + Close) / 3
            tp = (high + low + close) / 3.0

            cumulative_tp_volume += tp * volume
            cumulative_volume += volume

        if cumulative_volume == 0:
            return None

        return cumulative_tp_volume / cumulative_volume

    @staticmethod
    def calculate_vwap_bands(
        candles: list[dict[str, float]],
        highs: list[float],
        lows: list[float],
        closes: list[float],
        atr_period: int = 14,
    ) -> dict[str, Optional[float]]:
        """Calculate VWAP Bands (VWAP ± 1 ATR).

        VWAP Bands provide dynamic support/resistance based on volatility (ATR).
        - VWAP Upper = VWAP + ATR
        - VWAP Lower = VWAP - ATR

        Args:
            candles: List of dicts with 'high', 'low', 'close', 'volume' keys
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            atr_period: ATR period (default 14)

        Returns:
            Dict with 'vwap', 'vwap_upper', 'vwap_lower'
        """
        if not candles or len(candles) < atr_period + 1:
            return {"vwap": None, "vwap_upper": None, "vwap_lower": None}

        # Calculate VWAP
        vwap = IndicatorService.calculate_vwap(candles)

        # Calculate ATR
        atr_vals = IndicatorService.calculate_atr(highs, lows, closes, atr_period)
        atr = atr_vals[-1] if atr_vals and atr_vals[-1] is not None else None

        if vwap is None or atr is None:
            return {"vwap": vwap, "vwap_upper": None, "vwap_lower": None}

        vwap_upper = vwap + atr
        vwap_lower = vwap - atr

        return {
            "vwap": vwap,
            "vwap_upper": vwap_upper,
            "vwap_lower": vwap_lower,
        }

    @staticmethod
    def calculate_adx(
        highs: list[float], lows: list[float], closes: list[float], period: int = 14
    ) -> Optional[float]:
        """Calculate Average Directional Index (ADX) using TA-Lib.

        ADX measures trend strength:
        - ADX > 25: Strong trend
        - ADX 15-25: Weak trend
        - ADX < 15: Choppy (avoid)

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            period: ADX period (default 14)

        Returns:
            Current ADX value (0-100) or None if insufficient data
        """
        if not highs or not lows or not closes or len(closes) < period + 1:
            return None

        adx_values = talib.ADX(
            _to_array(highs), _to_array(lows), _to_array(closes), timeperiod=period
        )
        cleaned = _clean_result(adx_values)
        return cleaned[-1] if cleaned and cleaned[-1] is not None else None

    @staticmethod
    def calculate_obv(closes: list[float], volumes: list[float], obv_ma_period: int = 14) -> tuple[float, float, bool]:
        """Calculate On-Balance Volume (OBV) and trend.

        OBV detects whale accumulation/distribution:
        - If close > prev_close: obv += volume
        - If close < prev_close: obv -= volume
        - If close == prev_close: obv stays same
        - obv_trending = current_obv > obv_ma

        Args:
            closes: List of close prices
            volumes: List of volumes
            obv_ma_period: Period for OBV moving average (default 14)

        Returns:
            Tuple of (current_obv, obv_ma, obv_trending)
        """
        if not closes or not volumes or len(closes) != len(volumes):
            return 0.0, 0.0, False

        if len(closes) < obv_ma_period + 1:
            return 0.0, 0.0, False

        # Calculate OBV values
        obv_values = []
        obv = 0.0

        for i in range(len(closes)):
            if i == 0:
                obv = float(volumes[0])
            else:
                if closes[i] > closes[i - 1]:
                    obv += float(volumes[i])
                elif closes[i] < closes[i - 1]:
                    obv -= float(volumes[i])
                # If close == prev_close, obv stays same (no change)

            obv_values.append(obv)

        # Calculate OBV moving average
        obv_ma_vals = IndicatorService.calculate_sma(obv_values, obv_ma_period)
        obv_ma = obv_ma_vals[-1] if obv_ma_vals and obv_ma_vals[-1] is not None else 0.0

        # Current OBV and trend
        current_obv = obv_values[-1]
        obv_trending = current_obv > obv_ma

        return current_obv, obv_ma, obv_trending

    @staticmethod
    def calculate_ichimoku(
        highs: list[float],
        lows: list[float],
        closes: list[float],
    ) -> dict[str, Any]:
        """Calculate Ichimoku Cloud (full Kumo + Senkou + Kijun).

        Ichimoku provides complete market structure understanding:
        - Tenkan-sen (Conversion Line): 9-period high/low midpoint
        - Kijun-sen (Base Line): 26-period high/low midpoint
        - Senkou A (Leading Span A): (Tenkan + Kijun) / 2, plotted 26 periods ahead
        - Senkou B (Leading Span B): 52-period high/low midpoint, plotted 26 periods ahead
        - Kumo (Cloud): Area between Senkou A and B
        - Chikou (Lagging Span): Current close plotted 26 periods back

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices

        Returns:
            Dictionary with all Ichimoku components and signals
        """
        if not highs or not lows or not closes or len(closes) < 52:
            # Need at least 52 periods for full Ichimoku
            return {
                "tenkan": None,
                "kijun": None,
                "senkou_a": None,
                "senkou_b": None,
                "senkou_a_future": [],
                "senkou_b_future": [],
                "chikou": None,
                "kumo_high": None,
                "kumo_low": None,
                "signals": {},
            }

        # Calculate Tenkan-sen (9-period high/low midpoint)
        tenkan = (max(highs[-9:]) + min(lows[-9:])) / 2.0

        # Calculate Kijun-sen (26-period high/low midpoint)
        kijun = (max(highs[-26:]) + min(lows[-26:])) / 2.0

        # Calculate Senkou A (plotted 26 periods ahead)
        senkou_a = (tenkan + kijun) / 2.0

        # Calculate Senkou B (52-period high/low midpoint, plotted 26 periods ahead)
        senkou_b = (max(highs[-52:]) + min(lows[-52:])) / 2.0

        # Calculate Chikou (current close plotted 26 periods back)
        # This is just the current close, but in practice it's shifted back 26 bars
        chikou = closes[-1]

        # Calculate historical Senkou A and B values for cloud visualization
        # These are shifted 26 periods forward
        senkou_a_future: list[Optional[float]] = [None] * 26
        senkou_b_future: list[Optional[float]] = [None] * 26

        for i in range(52, len(closes)):
            # Tenkan for this period
            tenkan_hist = (max(highs[i-9:i+1]) + min(lows[i-9:i+1])) / 2.0
            # Kijun for this period
            kijun_hist = (max(highs[i-26:i+1]) + min(lows[i-26:i+1])) / 2.0
            # Senkou A for this period (plotted 26 ahead)
            senkou_a_val = (tenkan_hist + kijun_hist) / 2.0
            # Senkou B for this period (plotted 26 ahead)
            senkou_b_val = (max(highs[i-52:i+1]) + min(lows[i-52:i+1])) / 2.0

            senkou_a_future.append(senkou_a_val)
            senkou_b_future.append(senkou_b_val)

        # Calculate current Kumo (cloud) boundaries
        current_price = closes[-1]

        # Kumo top/bottom is based on the most recent Senkou A and B
        # We need the values from 26 bars ago (since they're plotted 26 ahead)
        if len(senkou_a_future) >= 27:
            kumo_senkou_a_current = senkou_a_future[-27]
            kumo_senkou_b_current = senkou_b_future[-27]
        else:
            kumo_senkou_a_current = None
            kumo_senkou_b_current = None

        if kumo_senkou_a_current is not None and kumo_senkou_b_current is not None:
            kumo_high = max(kumo_senkou_a_current, kumo_senkou_b_current)
            kumo_low = min(kumo_senkou_a_current, kumo_senkou_b_current)
        else:
            kumo_high = None
            kumo_low = None

        # Generate Ichimoku signals
        signals: dict[str, bool | None] = {}

        if kumo_high is not None and kumo_low is not None:
            # Price vs Kumo signals
            signals["price_above_kumo"] = current_price > kumo_high
            signals["price_below_kumo"] = current_price < kumo_low
            signals["price_in_kumo"] = not signals["price_above_kumo"] and not signals["price_below_kumo"]

            # Tenkan vs Kijun signal (bullish structure)
            signals["tenkan_above_kijun"] = tenkan > kijun

            # Cloud orientation
            signals["kumo_bullish"] = kumo_senkou_a_current > kumo_senkou_b_current if kumo_senkou_a_current is not None else None

            # Chikou vs price signal
            if len(closes) >= 27:
                price_26_bars_ago = closes[-27]
                signals["chikou_above_price"] = chikou > price_26_bars_ago
            else:
                signals["chikou_above_price"] = None

            # Cloud crossing detection (comparing with previous values)
            if len(senkou_a_future) >= 28:
                prev_kumo_a = senkou_a_future[-28]
                prev_kumo_b = senkou_b_future[-28]
                if prev_kumo_a is not None and prev_kumo_b is not None:
                    prev_kumo_high = max(prev_kumo_a, prev_kumo_b)
                    prev_kumo_low = min(prev_kumo_a, prev_kumo_b)

                    # Check for bullish cloud crossing
                    prev_price = closes[-2] if len(closes) >= 2 else closes[-1]
                    signals["cloud_bullish_cross"] = (prev_price < prev_kumo_low) and (current_price > kumo_low)
                    signals["cloud_bearish_cross"] = (prev_price > prev_kumo_high) and (current_price < kumo_high)

                    # Cloud expansion/squeeze
                    current_kumo_width = kumo_high - kumo_low
                    prev_kumo_width = prev_kumo_high - prev_kumo_low
                    median_width = (current_kumo_width + prev_kumo_width) / 2.0

                    signals["cloud_expansion"] = current_kumo_width > median_width * 1.2
                    signals["cloud_squeeze"] = current_kumo_width < median_width * 0.8
                else:
                    signals["cloud_bullish_cross"] = None
                    signals["cloud_bearish_cross"] = None
                    signals["cloud_expansion"] = None
                    signals["cloud_squeeze"] = None
            else:
                signals["cloud_bullish_cross"] = None
                signals["cloud_bearish_cross"] = None
                signals["cloud_expansion"] = None
                signals["cloud_squeeze"] = None
        else:
            # Insufficient data
            signals["price_above_kumo"] = None
            signals["price_below_kumo"] = None
            signals["price_in_kumo"] = None
            signals["tenkan_above_kijun"] = None
            signals["kumo_bullish"] = None
            signals["chikou_above_price"] = None
            signals["cloud_bullish_cross"] = None
            signals["cloud_bearish_cross"] = None
            signals["cloud_expansion"] = None
            signals["cloud_squeeze"] = None

        # Log Ichimoku state
        logger.debug(
            f"[ICHIMOKU] Price: {current_price:.2f}, Kumo: {kumo_high:.2f}-{kumo_low:.2f}, "
            f"Tenkan/Kijun: {tenkan:.2f}/{kijun:.2f}, "
            f"Signals: {sum(1 for v in signals.values() if v is True)}/{len(signals)}"
        )

        return {
            "tenkan": tenkan,
            "kijun": kijun,
            "senkou_a": senkou_a,
            "senkou_b": senkou_b,
            "senkou_a_future": senkou_a_future,
            "senkou_b_future": senkou_b_future,
            "chikou": chikou,
            "kumo_high": kumo_high,
            "kumo_low": kumo_low,
            "signals": signals,
        }

    @staticmethod
    def calculate_all_indicators(
        closes: list[float],
        highs: Optional[list[float]] = None,
        lows: Optional[list[float]] = None,
    ) -> dict[str, Any]:
        """Calculate all commonly used indicators at once."""
        indicators = {
            "ema_20": IndicatorService.calculate_ema(closes, 20),
            "ema_50": IndicatorService.calculate_ema(closes, 50),
            "sma_20": IndicatorService.calculate_sma(closes, 20),
            "rsi_14": IndicatorService.calculate_rsi(closes, 14),
            "macd": IndicatorService.calculate_macd(closes),
            "bb": IndicatorService.calculate_bollinger_bands(closes),
        }

        if highs and lows:
            indicators["atr_14"] = IndicatorService.calculate_atr(highs, lows, closes, 14)
            indicators["stoch"] = IndicatorService.calculate_stochastic(highs, lows, closes)

        return indicators
    
    @staticmethod
    def get_latest_values(indicators: dict[str, Any]) -> dict[str, Any]:
        """Extract the latest (most recent) value from each indicator."""

        def get_latest(values: list[Any]) -> Optional[float]:
            """Get the last non-None value from a list."""
            if not values:
                return None
            for val in reversed(values):
                if val is not None:
                    return float(val) if isinstance(val, (int, float)) else None
            return None

        latest: dict[str, Any] = {}
        for key, value in indicators.items():
            if isinstance(value, dict):
                latest[key] = {sub_key: get_latest(sub_val) if isinstance(sub_val, list) else None
                              for sub_key, sub_val in value.items()}
            elif isinstance(value, list):
                latest[key] = get_latest(value)
            else:
                latest[key] = None

        return latest


class CachedIndicatorService:
    """Indicator service with caching support for expensive calculations."""

    def __init__(self, cache_service: Optional[Any] = None) -> None:
        """Initialize cached indicator service.

        Args:
            cache_service: Optional CacheService instance for caching indicators
        """
        self.cache_service = cache_service
        self.indicator_service = IndicatorService

    async def calculate_ema_cached(
        self,
        prices: list[float],
        symbol: str,
        timeframe: str,
        period: int = 20,
    ) -> list[Optional[float]]:
        """Calculate EMA with optional caching.

        Args:
            prices: List of prices
            symbol: Trading symbol (for cache key)
            timeframe: Timeframe (for cache key)
            period: EMA period

        Returns:
            List of EMA values
        """
        if not self.cache_service:
            return self.indicator_service.calculate_ema(prices, period)

        try:
            cache_key = await self.cache_service.get_ema_cache_key(symbol, timeframe, period)
            cached = await self.cache_service.get_cached(cache_key)

            if cached is not None:
                logger.debug(f"EMA cache hit (symbol={symbol}, timeframe={timeframe}, period={period})")
                return cached  # type: ignore[no-any-return]

            result = self.indicator_service.calculate_ema(prices, period)
            if self.cache_service:
                await self.cache_service.set_cached(
                    cache_key,
                    result,
                    ttl=self.cache_service.TTL_INDICATOR,
                )
            return result
        except Exception as e:
            logger.error(f"Error in cached EMA calculation: {e}")
            # Fallback to uncached calculation
            return self.indicator_service.calculate_ema(prices, period)

    async def calculate_sma_cached(
        self,
        prices: list[float],
        symbol: str,
        timeframe: str,
        period: int = 20,
    ) -> list[Optional[float]]:
        """Calculate SMA with optional caching.

        Args:
            prices: List of prices
            symbol: Trading symbol (for cache key)
            timeframe: Timeframe (for cache key)
            period: SMA period

        Returns:
            List of SMA values
        """
        if not self.cache_service:
            return self.indicator_service.calculate_sma(prices, period)

        try:
            cache_key = await self.cache_service.get_sma_cache_key(symbol, timeframe, period)
            cached = await self.cache_service.get_cached(cache_key)

            if cached is not None:
                logger.debug(f"SMA cache hit (symbol={symbol}, timeframe={timeframe}, period={period})")
                return cached  # type: ignore[no-any-return]

            result = self.indicator_service.calculate_sma(prices, period)
            if self.cache_service:
                await self.cache_service.set_cached(
                    cache_key,
                    result,
                    ttl=self.cache_service.TTL_INDICATOR,
                )
            return result
        except Exception as e:
            logger.error(f"Error in cached SMA calculation: {e}")
            # Fallback to uncached calculation
            return self.indicator_service.calculate_sma(prices, period)

    async def calculate_rsi_cached(
        self,
        prices: list[float],
        symbol: str,
        timeframe: str,
        period: int = 14,
    ) -> list[Optional[float]]:
        """Calculate RSI with optional caching.

        Args:
            prices: List of prices
            symbol: Trading symbol (for cache key)
            timeframe: Timeframe (for cache key)
            period: RSI period

        Returns:
            List of RSI values
        """
        if not self.cache_service:
            return self.indicator_service.calculate_rsi(prices, period)

        try:
            cache_key = await self.cache_service.get_rsi_cache_key(symbol, timeframe, period)
            cached = await self.cache_service.get_cached(cache_key)

            if cached is not None:
                logger.debug(f"RSI cache hit (symbol={symbol}, timeframe={timeframe}, period={period})")
                return cached  # type: ignore[no-any-return]

            result = self.indicator_service.calculate_rsi(prices, period)
            if self.cache_service:
                await self.cache_service.set_cached(
                    cache_key,
                    result,
                    ttl=self.cache_service.TTL_INDICATOR,
                )
            return result
        except Exception as e:
            logger.error(f"Error in cached RSI calculation: {e}")
            # Fallback to uncached calculation
            return self.indicator_service.calculate_rsi(prices, period)

    async def calculate_macd_cached(
        self,
        prices: list[float],
        symbol: str,
        timeframe: str,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> dict[str, list[Optional[float]]]:
        """Calculate MACD with optional caching.

        Args:
            prices: List of prices
            symbol: Trading symbol (for cache key)
            timeframe: Timeframe (for cache key)
            fast_period: MACD fast period
            slow_period: MACD slow period
            signal_period: MACD signal period

        Returns:
            Dictionary with MACD, signal, and histogram values
        """
        if not self.cache_service:
            return self.indicator_service.calculate_macd(
                prices, fast_period, slow_period, signal_period
            )

        try:
            cache_key = await self.cache_service.get_macd_cache_key(symbol, timeframe)
            cached = await self.cache_service.get_cached(cache_key)

            if cached is not None:
                logger.debug(f"MACD cache hit (symbol={symbol}, timeframe={timeframe})")
                return cached  # type: ignore[no-any-return]

            result = self.indicator_service.calculate_macd(
                prices, fast_period, slow_period, signal_period
            )
            if self.cache_service:
                await self.cache_service.set_cached(
                    cache_key,
                    result,
                    ttl=self.cache_service.TTL_INDICATOR,
                )
            return result
        except Exception as e:
            logger.error(f"Error in cached MACD calculation: {e}")
            # Fallback to uncached calculation
            return self.indicator_service.calculate_macd(
                prices, fast_period, slow_period, signal_period
            )

    async def invalidate_indicator_cache(self, symbol: str, timeframe: str) -> int:
        """Invalidate all indicator caches for a symbol/timeframe.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe

        Returns:
            Number of cache keys deleted
        """
        if not self.cache_service:
            return 0

        pattern = f"cache:indicator:*:{symbol}:{timeframe}*"
        result = await self.cache_service.invalidate_pattern(pattern)
        return result if isinstance(result, int) else 0


# Singleton instance
_cached_indicator_service: Optional[CachedIndicatorService] = None


async def get_cached_indicator_service(
    cache_service: Optional[Any] = None,
) -> CachedIndicatorService:
    """Get cached indicator service instance (FastAPI dependency).

    Args:
        cache_service: Optional CacheService instance

    Returns:
        CachedIndicatorService instance
    """
    global _cached_indicator_service
    if _cached_indicator_service is None:
        if cache_service is None:
            # Try to import and get cache service
            try:
                from .cache_service import get_cache_service
                cache_service = await get_cache_service()
            except ImportError:
                pass
        _cached_indicator_service = CachedIndicatorService(cache_service)
    return _cached_indicator_service