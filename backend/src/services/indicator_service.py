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
    ) -> dict[str, list[Optional[float]]]:
        """Calculate Bollinger Bands. Returns dict with 'upper', 'middle', 'lower' lists."""
        upper, middle, lower = talib.BBANDS(
            _to_array(prices), timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev
        )
        return {
            "upper": _clean_result(upper),
            "middle": _clean_result(middle),
            "lower": _clean_result(lower),
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