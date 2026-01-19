"""Comprehensive test suite for indicator caching."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import numpy as np

from src.services.indicator_service import (
    IndicatorService,
    CachedIndicatorService,
    get_cached_indicator_service,
)


class TestIndicatorServiceBasics:
    """Tests for basic indicator calculations (without caching)."""

    def test_calculate_ema_basic(self):
        """Test basic EMA calculation."""
        prices = [100, 101, 102, 103, 104, 105]
        result = IndicatorService.calculate_ema(prices, period=3)

        assert isinstance(result, list)
        assert len(result) == len(prices)
        # First few values should be None (insufficient data)
        assert result[0] is None
        # Later values should be numeric
        assert any(v is not None for v in result)

    def test_calculate_sma_basic(self):
        """Test basic SMA calculation."""
        prices = [100, 101, 102, 103, 104, 105]
        result = IndicatorService.calculate_sma(prices, period=3)

        assert isinstance(result, list)
        assert len(result) == len(prices)
        # First period-1 values should be None
        assert result[0] is None
        assert result[1] is None
        # Third value should be average of first 3: (100+101+102)/3
        assert result[2] == pytest.approx(101.0)

    def test_calculate_rsi_basic(self):
        """Test basic RSI calculation."""
        prices = [100 + i for i in range(20)]  # Uptrend
        result = IndicatorService.calculate_rsi(prices, period=14)

        assert isinstance(result, list)
        assert len(result) == len(prices)
        # RSI should be between 0 and 100 (or None)
        for val in result:
            if val is not None:
                assert 0 <= val <= 100

    def test_calculate_macd_basic(self):
        """Test basic MACD calculation."""
        prices = [100 + (i * 0.5) for i in range(30)]
        result = IndicatorService.calculate_macd(prices)

        assert isinstance(result, dict)
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result
        assert len(result["macd"]) == len(prices)
        assert len(result["signal"]) == len(prices)
        assert len(result["histogram"]) == len(prices)


class TestCachedIndicatorServiceBasics:
    """Tests for CachedIndicatorService without actual caching."""

    @pytest.mark.asyncio
    async def test_ema_without_cache(self):
        """Test EMA calculation without cache service."""
        service = CachedIndicatorService(cache_service=None)
        prices = [100, 101, 102, 103, 104, 105]

        result = await service.calculate_ema_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=3
        )

        assert isinstance(result, list)
        assert len(result) == len(prices)

    @pytest.mark.asyncio
    async def test_sma_without_cache(self):
        """Test SMA calculation without cache service."""
        service = CachedIndicatorService(cache_service=None)
        prices = [100, 101, 102, 103, 104, 105]

        result = await service.calculate_sma_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=3
        )

        assert isinstance(result, list)
        assert len(result) == len(prices)

    @pytest.mark.asyncio
    async def test_rsi_without_cache(self):
        """Test RSI calculation without cache service."""
        service = CachedIndicatorService(cache_service=None)
        prices = [100 + i for i in range(20)]

        result = await service.calculate_rsi_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=14
        )

        assert isinstance(result, list)
        assert len(result) == len(prices)

    @pytest.mark.asyncio
    async def test_macd_without_cache(self):
        """Test MACD calculation without cache service."""
        service = CachedIndicatorService(cache_service=None)
        prices = [100 + (i * 0.5) for i in range(30)]

        result = await service.calculate_macd_cached(
            prices, symbol="BTC/USDT", timeframe="1h"
        )

        assert isinstance(result, dict)
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result


class TestCachedIndicatorServiceWithMocking:
    """Tests for CachedIndicatorService with mocked cache."""

    @pytest.mark.asyncio
    async def test_ema_cache_hit(self):
        """Test EMA returns cached value on hit."""
        mock_cache = AsyncMock()
        cached_result = [None, None, 101.5, 102.0, 103.0, 104.0]
        mock_cache.get_cached.return_value = cached_result
        mock_cache.get_ema_cache_key.return_value = "cache:indicator:ema:BTC/USDT:1h:3"
        mock_cache.TTL_INDICATOR = 15 * 60

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100, 101, 102, 103, 104, 105]

        result = await service.calculate_ema_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=3
        )

        assert result == cached_result
        mock_cache.get_cached.assert_called_once()
        # set_cached should not be called since cache hit
        mock_cache.set_cached.assert_not_called()

    @pytest.mark.asyncio
    async def test_ema_cache_miss(self):
        """Test EMA calculates and caches on miss."""
        mock_cache = AsyncMock()
        mock_cache.get_cached.return_value = None  # Cache miss
        mock_cache.get_ema_cache_key.return_value = "cache:indicator:ema:BTC/USDT:1h:3"
        mock_cache.TTL_INDICATOR = 15 * 60
        mock_cache.set_cached.return_value = True

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100, 101, 102, 103, 104, 105]

        result = await service.calculate_ema_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=3
        )

        assert isinstance(result, list)
        assert len(result) == len(prices)
        mock_cache.get_cached.assert_called_once()
        mock_cache.set_cached.assert_called_once()

    @pytest.mark.asyncio
    async def test_sma_cache_hit(self):
        """Test SMA returns cached value on hit."""
        mock_cache = AsyncMock()
        cached_result = [None, None, 101.0, 102.0, 103.0, 104.0]
        mock_cache.get_cached.return_value = cached_result
        mock_cache.get_sma_cache_key.return_value = "cache:indicator:sma:BTC/USDT:1h:3"
        mock_cache.TTL_INDICATOR = 15 * 60

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100, 101, 102, 103, 104, 105]

        result = await service.calculate_sma_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=3
        )

        assert result == cached_result
        mock_cache.get_cached.assert_called_once()
        mock_cache.set_cached.assert_not_called()

    @pytest.mark.asyncio
    async def test_sma_cache_miss(self):
        """Test SMA calculates and caches on miss."""
        mock_cache = AsyncMock()
        mock_cache.get_cached.return_value = None  # Cache miss
        mock_cache.get_sma_cache_key.return_value = "cache:indicator:sma:BTC/USDT:1h:3"
        mock_cache.TTL_INDICATOR = 15 * 60
        mock_cache.set_cached.return_value = True

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100, 101, 102, 103, 104, 105]

        result = await service.calculate_sma_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=3
        )

        assert isinstance(result, list)
        assert len(result) == len(prices)
        mock_cache.get_cached.assert_called_once()
        mock_cache.set_cached.assert_called_once()

    @pytest.mark.asyncio
    async def test_rsi_cache_hit(self):
        """Test RSI returns cached value on hit."""
        mock_cache = AsyncMock()
        cached_result = [None] * 13 + [70.0, 75.0, 80.0, 85.0, 90.0, 95.0, 100.0]
        mock_cache.get_cached.return_value = cached_result
        mock_cache.get_rsi_cache_key.return_value = "cache:indicator:rsi:BTC/USDT:1h:14"
        mock_cache.TTL_INDICATOR = 15 * 60

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100 + i for i in range(20)]

        result = await service.calculate_rsi_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=14
        )

        assert result == cached_result
        mock_cache.get_cached.assert_called_once()
        mock_cache.set_cached.assert_not_called()

    @pytest.mark.asyncio
    async def test_rsi_cache_miss(self):
        """Test RSI calculates and caches on miss."""
        mock_cache = AsyncMock()
        mock_cache.get_cached.return_value = None  # Cache miss
        mock_cache.get_rsi_cache_key.return_value = "cache:indicator:rsi:BTC/USDT:1h:14"
        mock_cache.TTL_INDICATOR = 15 * 60
        mock_cache.set_cached.return_value = True

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100 + i for i in range(20)]

        result = await service.calculate_rsi_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=14
        )

        assert isinstance(result, list)
        assert len(result) == len(prices)
        mock_cache.get_cached.assert_called_once()
        mock_cache.set_cached.assert_called_once()

    @pytest.mark.asyncio
    async def test_macd_cache_hit(self):
        """Test MACD returns cached value on hit."""
        mock_cache = AsyncMock()
        cached_result = {
            "macd": [None] * 25 + [0.5, 1.0, 1.5],
            "signal": [None] * 33 + [0.3, 0.7],
            "histogram": [None] * 34 + [0.2],
        }
        mock_cache.get_cached.return_value = cached_result
        mock_cache.get_macd_cache_key.return_value = "cache:indicator:macd:BTC/USDT:1h"
        mock_cache.TTL_INDICATOR = 15 * 60

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100 + (i * 0.5) for i in range(35)]

        result = await service.calculate_macd_cached(
            prices, symbol="BTC/USDT", timeframe="1h"
        )

        assert result == cached_result
        mock_cache.get_cached.assert_called_once()
        mock_cache.set_cached.assert_not_called()

    @pytest.mark.asyncio
    async def test_macd_cache_miss(self):
        """Test MACD calculates and caches on miss."""
        mock_cache = AsyncMock()
        mock_cache.get_cached.return_value = None  # Cache miss
        mock_cache.get_macd_cache_key.return_value = "cache:indicator:macd:BTC/USDT:1h"
        mock_cache.TTL_INDICATOR = 15 * 60
        mock_cache.set_cached.return_value = True

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100 + (i * 0.5) for i in range(35)]

        result = await service.calculate_macd_cached(
            prices, symbol="BTC/USDT", timeframe="1h"
        )

        assert isinstance(result, dict)
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result
        mock_cache.get_cached.assert_called_once()
        mock_cache.set_cached.assert_called_once()


class TestCachedIndicatorServiceCacheKeyGeneration:
    """Tests for cache key generation."""

    @pytest.mark.asyncio
    async def test_ema_cache_key_format(self):
        """Test EMA cache key is generated correctly."""
        mock_cache = AsyncMock()
        mock_cache.get_cached.return_value = None
        mock_cache.get_ema_cache_key.return_value = "cache:indicator:ema:BTC/USDT:1h:20"
        mock_cache.TTL_INDICATOR = 15 * 60
        mock_cache.set_cached.return_value = True

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100 + i for i in range(50)]

        await service.calculate_ema_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=20
        )

        mock_cache.get_ema_cache_key.assert_called_once_with("BTC/USDT", "1h", 20)

    @pytest.mark.asyncio
    async def test_sma_cache_key_format(self):
        """Test SMA cache key is generated correctly."""
        mock_cache = AsyncMock()
        mock_cache.get_cached.return_value = None
        mock_cache.get_sma_cache_key.return_value = "cache:indicator:sma:ETH/USDT:4h:50"
        mock_cache.TTL_INDICATOR = 15 * 60
        mock_cache.set_cached.return_value = True

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100 + (i * 0.5) for i in range(100)]

        await service.calculate_sma_cached(
            prices, symbol="ETH/USDT", timeframe="4h", period=50
        )

        mock_cache.get_sma_cache_key.assert_called_once_with("ETH/USDT", "4h", 50)

    @pytest.mark.asyncio
    async def test_rsi_cache_key_format(self):
        """Test RSI cache key is generated correctly."""
        mock_cache = AsyncMock()
        mock_cache.get_cached.return_value = None
        mock_cache.get_rsi_cache_key.return_value = "cache:indicator:rsi:ADA/USDT:15m:14"
        mock_cache.TTL_INDICATOR = 15 * 60
        mock_cache.set_cached.return_value = True

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100 + i for i in range(50)]

        await service.calculate_rsi_cached(
            prices, symbol="ADA/USDT", timeframe="15m", period=14
        )

        mock_cache.get_rsi_cache_key.assert_called_once_with("ADA/USDT", "15m", 14)

    @pytest.mark.asyncio
    async def test_macd_cache_key_format(self):
        """Test MACD cache key is generated correctly."""
        mock_cache = AsyncMock()
        mock_cache.get_cached.return_value = None
        mock_cache.get_macd_cache_key.return_value = "cache:indicator:macd:XRP/USDT:1d"
        mock_cache.TTL_INDICATOR = 15 * 60
        mock_cache.set_cached.return_value = True

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100 + (i * 0.1) for i in range(100)]

        await service.calculate_macd_cached(
            prices, symbol="XRP/USDT", timeframe="1d"
        )

        mock_cache.get_macd_cache_key.assert_called_once_with("XRP/USDT", "1d")


class TestCachedIndicatorServiceTTL:
    """Tests for TTL configuration."""

    @pytest.mark.asyncio
    async def test_ema_ttl_15_minutes(self):
        """Test EMA is cached with 15-minute TTL."""
        mock_cache = AsyncMock()
        mock_cache.get_cached.return_value = None
        mock_cache.get_ema_cache_key.return_value = "cache:indicator:ema:BTC/USDT:1h:20"
        mock_cache.TTL_INDICATOR = 15 * 60  # 900 seconds
        mock_cache.set_cached.return_value = True

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100 + i for i in range(50)]

        await service.calculate_ema_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=20
        )

        # Verify set_cached was called with TTL_INDICATOR
        call_args = mock_cache.set_cached.call_args
        assert call_args[1]["ttl"] == 15 * 60

    @pytest.mark.asyncio
    async def test_sma_ttl_15_minutes(self):
        """Test SMA is cached with 15-minute TTL."""
        mock_cache = AsyncMock()
        mock_cache.get_cached.return_value = None
        mock_cache.get_sma_cache_key.return_value = "cache:indicator:sma:BTC/USDT:1h:20"
        mock_cache.TTL_INDICATOR = 15 * 60
        mock_cache.set_cached.return_value = True

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100 + i for i in range(50)]

        await service.calculate_sma_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=20
        )

        call_args = mock_cache.set_cached.call_args
        assert call_args[1]["ttl"] == 15 * 60

    @pytest.mark.asyncio
    async def test_rsi_ttl_15_minutes(self):
        """Test RSI is cached with 15-minute TTL."""
        mock_cache = AsyncMock()
        mock_cache.get_cached.return_value = None
        mock_cache.get_rsi_cache_key.return_value = "cache:indicator:rsi:BTC/USDT:1h:14"
        mock_cache.TTL_INDICATOR = 15 * 60
        mock_cache.set_cached.return_value = True

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100 + i for i in range(50)]

        await service.calculate_rsi_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=14
        )

        call_args = mock_cache.set_cached.call_args
        assert call_args[1]["ttl"] == 15 * 60

    @pytest.mark.asyncio
    async def test_macd_ttl_15_minutes(self):
        """Test MACD is cached with 15-minute TTL."""
        mock_cache = AsyncMock()
        mock_cache.get_cached.return_value = None
        mock_cache.get_macd_cache_key.return_value = "cache:indicator:macd:BTC/USDT:1h"
        mock_cache.TTL_INDICATOR = 15 * 60
        mock_cache.set_cached.return_value = True

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100 + (i * 0.5) for i in range(100)]

        await service.calculate_macd_cached(
            prices, symbol="BTC/USDT", timeframe="1h"
        )

        call_args = mock_cache.set_cached.call_args
        assert call_args[1]["ttl"] == 15 * 60


class TestCachedIndicatorServiceErrorHandling:
    """Tests for error handling and fallback behavior."""

    @pytest.mark.asyncio
    async def test_ema_cache_error_fallback(self):
        """Test EMA falls back to uncached calculation on cache error."""
        mock_cache = AsyncMock()
        mock_cache.get_cached.side_effect = Exception("Redis connection failed")
        mock_cache.get_ema_cache_key.return_value = "cache:indicator:ema:BTC/USDT:1h:20"

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100 + i for i in range(50)]

        # Should not raise, should return calculated result
        result = await service.calculate_ema_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=20
        )

        assert isinstance(result, list)
        assert len(result) == len(prices)

    @pytest.mark.asyncio
    async def test_sma_cache_error_fallback(self):
        """Test SMA falls back to uncached calculation on cache error."""
        mock_cache = AsyncMock()
        mock_cache.get_cached.side_effect = Exception("Redis connection failed")
        mock_cache.get_sma_cache_key.return_value = "cache:indicator:sma:BTC/USDT:1h:20"

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100 + i for i in range(50)]

        result = await service.calculate_sma_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=20
        )

        assert isinstance(result, list)
        assert len(result) == len(prices)

    @pytest.mark.asyncio
    async def test_rsi_cache_error_fallback(self):
        """Test RSI falls back to uncached calculation on cache error."""
        mock_cache = AsyncMock()
        mock_cache.get_cached.side_effect = Exception("Redis connection failed")
        mock_cache.get_rsi_cache_key.return_value = "cache:indicator:rsi:BTC/USDT:1h:14"

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100 + i for i in range(50)]

        result = await service.calculate_rsi_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=14
        )

        assert isinstance(result, list)
        assert len(result) == len(prices)

    @pytest.mark.asyncio
    async def test_macd_cache_error_fallback(self):
        """Test MACD falls back to uncached calculation on cache error."""
        mock_cache = AsyncMock()
        mock_cache.get_cached.side_effect = Exception("Redis connection failed")
        mock_cache.get_macd_cache_key.return_value = "cache:indicator:macd:BTC/USDT:1h"

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100 + (i * 0.5) for i in range(100)]

        result = await service.calculate_macd_cached(
            prices, symbol="BTC/USDT", timeframe="1h"
        )

        assert isinstance(result, dict)
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result


class TestCachedIndicatorServiceInvalidation:
    """Tests for cache invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_indicator_cache_success(self):
        """Test cache invalidation for symbol/timeframe."""
        mock_cache = AsyncMock()
        mock_cache.invalidate_pattern.return_value = 5  # 5 keys deleted

        service = CachedIndicatorService(cache_service=mock_cache)

        result = await service.invalidate_indicator_cache("BTC/USDT", "1h")

        assert result == 5
        mock_cache.invalidate_pattern.assert_called_once()
        # Verify pattern includes symbol and timeframe
        call_args = mock_cache.invalidate_pattern.call_args[0][0]
        assert "BTC/USDT" in call_args
        assert "1h" in call_args

    @pytest.mark.asyncio
    async def test_invalidate_indicator_cache_no_cache_service(self):
        """Test invalidation returns 0 when no cache service."""
        service = CachedIndicatorService(cache_service=None)

        result = await service.invalidate_indicator_cache("BTC/USDT", "1h")

        assert result == 0

    @pytest.mark.asyncio
    async def test_invalidate_indicator_cache_pattern(self):
        """Test invalidation pattern is correct."""
        mock_cache = AsyncMock()
        mock_cache.invalidate_pattern.return_value = 0

        service = CachedIndicatorService(cache_service=mock_cache)

        await service.invalidate_indicator_cache("ETH/USDT", "4h")

        expected_pattern = "cache:indicator:*:ETH/USDT:4h*"
        mock_cache.invalidate_pattern.assert_called_once_with(expected_pattern)


class TestCachedIndicatorServiceDifferentSymbols:
    """Tests for handling different trading symbols."""

    @pytest.mark.asyncio
    async def test_ema_different_symbols(self):
        """Test EMA caching with different symbols doesn't collide."""
        mock_cache = AsyncMock()
        mock_cache.get_cached.return_value = None
        mock_cache.get_ema_cache_key.side_effect = [
            "cache:indicator:ema:BTC/USDT:1h:20",
            "cache:indicator:ema:ETH/USDT:1h:20",
        ]
        mock_cache.TTL_INDICATOR = 15 * 60
        mock_cache.set_cached.return_value = True

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100 + i for i in range(50)]

        # First call for BTC
        result1 = await service.calculate_ema_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=20
        )

        # Second call for ETH with different prices
        prices2 = [150 + i for i in range(50)]
        result2 = await service.calculate_ema_cached(
            prices2, symbol="ETH/USDT", timeframe="1h", period=20
        )

        # Both should have been called with different keys
        assert mock_cache.get_ema_cache_key.call_count == 2
        calls = mock_cache.get_ema_cache_key.call_args_list
        assert calls[0][0] == ("BTC/USDT", "1h", 20)
        assert calls[1][0] == ("ETH/USDT", "1h", 20)

    @pytest.mark.asyncio
    async def test_sma_different_timeframes(self):
        """Test SMA caching with different timeframes doesn't collide."""
        mock_cache = AsyncMock()
        mock_cache.get_cached.return_value = None
        mock_cache.get_sma_cache_key.side_effect = [
            "cache:indicator:sma:BTC/USDT:1h:20",
            "cache:indicator:sma:BTC/USDT:4h:20",
        ]
        mock_cache.TTL_INDICATOR = 15 * 60
        mock_cache.set_cached.return_value = True

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100 + i for i in range(50)]

        # First call for 1h
        await service.calculate_sma_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=20
        )

        # Second call for 4h
        await service.calculate_sma_cached(
            prices, symbol="BTC/USDT", timeframe="4h", period=20
        )

        # Both should have been called with different keys
        assert mock_cache.get_sma_cache_key.call_count == 2
        calls = mock_cache.get_sma_cache_key.call_args_list
        assert calls[0][0] == ("BTC/USDT", "1h", 20)
        assert calls[1][0] == ("BTC/USDT", "4h", 20)


class TestCachedIndicatorServiceEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_price_list(self):
        """Test handling of empty price list."""
        service = CachedIndicatorService(cache_service=None)
        prices = []

        result = await service.calculate_ema_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=20
        )

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_single_price_point(self):
        """Test handling of single price point."""
        service = CachedIndicatorService(cache_service=None)
        prices = [100.0]

        result = await service.calculate_sma_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=20
        )

        assert isinstance(result, list)
        assert len(result) == 1
        # Should be None since not enough data
        assert result[0] is None

    @pytest.mark.asyncio
    async def test_very_large_period(self):
        """Test handling of period larger than price list."""
        service = CachedIndicatorService(cache_service=None)
        prices = [100 + i for i in range(10)]

        result = await service.calculate_rsi_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=200
        )

        assert isinstance(result, list)
        # All should be None since period is too large
        assert all(v is None for v in result)

    @pytest.mark.asyncio
    async def test_cached_empty_result(self):
        """Test caching empty (all None) results."""
        mock_cache = AsyncMock()
        empty_result = [None, None, None, None]
        mock_cache.get_cached.return_value = None  # First call: miss
        mock_cache.get_rsi_cache_key.return_value = "cache:indicator:rsi:BTC/USDT:1h:14"
        mock_cache.TTL_INDICATOR = 15 * 60
        mock_cache.set_cached.return_value = True

        service = CachedIndicatorService(cache_service=mock_cache)
        prices = [100, 101, 102, 103]

        result = await service.calculate_rsi_cached(
            prices, symbol="BTC/USDT", timeframe="1h", period=14
        )

        # Should have stored the empty result
        mock_cache.set_cached.assert_called_once()
