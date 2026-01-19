"""Tests for cache service."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.cache_service import CacheService


@pytest.mark.asyncio
class TestCacheService:
    """Test suite for CacheService."""

    @pytest.fixture
    async def cache_service(self):
        """Create mock cache service for testing."""
        mock_redis = AsyncMock()
        service = CacheService(redis_client=mock_redis)
        return service

    # Basic Cache Operations Tests
    async def test_get_cached_success(self, cache_service):
        """Test successful cache retrieval."""
        key = "test_key"
        value = {"data": "test_value"}
        serialized = json.dumps(value)

        cache_service.redis_client.get = AsyncMock(return_value=serialized)
        cache_service.redis_client.incr = AsyncMock(return_value=1)
        cache_service.redis_client.expire = AsyncMock(return_value=True)

        result = await cache_service.get_cached(key)

        assert result == value
        cache_service.redis_client.get.assert_called_once_with(key)

    async def test_get_cached_miss(self, cache_service):
        """Test cache miss (key not found)."""
        key = "missing_key"
        cache_service.redis_client.get = AsyncMock(return_value=None)
        cache_service.redis_client.incr = AsyncMock(return_value=1)
        cache_service.redis_client.expire = AsyncMock(return_value=True)

        result = await cache_service.get_cached(key)

        assert result is None
        cache_service.redis_client.get.assert_called_once_with(key)

    async def test_set_cached_success(self, cache_service):
        """Test successful cache set."""
        key = "test_key"
        value = {"data": "test_value"}
        ttl = 300

        cache_service.redis_client.setex = AsyncMock(return_value=True)

        result = await cache_service.set_cached(key, value, ttl)

        assert result is True
        cache_service.redis_client.setex.assert_called_once()
        call_args = cache_service.redis_client.setex.call_args
        assert call_args[0][0] == key
        assert call_args[0][1] == ttl
        assert json.loads(call_args[0][2]) == value

    async def test_set_cached_failure(self, cache_service):
        """Test cache set failure."""
        key = "test_key"
        value = {"data": "test_value"}

        cache_service.redis_client.setex = AsyncMock(return_value=False)

        result = await cache_service.set_cached(key, value)

        assert result is False

    async def test_delete_cached_success(self, cache_service):
        """Test successful cache deletion."""
        key = "test_key"
        cache_service.redis_client.delete = AsyncMock(return_value=1)

        result = await cache_service.delete_cached(key)

        assert result is True
        cache_service.redis_client.delete.assert_called_once_with(key)

    async def test_delete_cached_not_found(self, cache_service):
        """Test delete of non-existent key."""
        key = "missing_key"
        cache_service.redis_client.delete = AsyncMock(return_value=0)

        result = await cache_service.delete_cached(key)

        assert result is False

    # TTL and Expiration Tests
    async def test_set_cached_with_default_ttl(self, cache_service):
        """Test cache set with default TTL."""
        key = "test_key"
        value = {"data": "test"}

        cache_service.redis_client.setex = AsyncMock(return_value=True)

        await cache_service.set_cached(key, value)

        call_args = cache_service.redis_client.setex.call_args
        assert call_args[0][1] == CacheService.TTL_MARKET_DATA  # Default 5 minutes

    async def test_set_cached_with_custom_ttl(self, cache_service):
        """Test cache set with custom TTL."""
        key = "test_key"
        value = {"data": "test"}
        custom_ttl = 1800  # 30 minutes

        cache_service.redis_client.setex = AsyncMock(return_value=True)

        await cache_service.set_cached(key, value, ttl=custom_ttl)

        call_args = cache_service.redis_client.setex.call_args
        assert call_args[0][1] == custom_ttl

    # Cache Key Generation Tests
    async def test_get_ohlcv_cache_key(self, cache_service):
        """Test OHLCV cache key generation."""
        key = await cache_service.get_ohlcv_cache_key("BTC/USDT", "1h")
        assert key == "cache:ohlcv:BTC/USDT:1h"

    async def test_get_ticker_cache_key(self, cache_service):
        """Test ticker cache key generation."""
        key = await cache_service.get_ticker_cache_key("BTC/USDT")
        assert key == "cache:ticker:BTC/USDT"

    async def test_get_funding_rate_cache_key(self, cache_service):
        """Test funding rate cache key generation."""
        key = await cache_service.get_funding_rate_cache_key("BTC/USDT")
        assert key == "cache:funding_rate:BTC/USDT"

    async def test_get_open_interest_cache_key(self, cache_service):
        """Test open interest cache key generation."""
        key = await cache_service.get_open_interest_cache_key("BTC/USDT")
        assert key == "cache:open_interest:BTC/USDT"

    async def test_get_market_snapshot_cache_key(self, cache_service):
        """Test market snapshot cache key generation."""
        key = await cache_service.get_market_snapshot_cache_key("BTC/USDT", "1h")
        assert key == "cache:market_snapshot:BTC/USDT:1h"

    async def test_get_market_snapshot_multi_cache_key(self, cache_service):
        """Test multi-timeframe market snapshot cache key generation."""
        key = await cache_service.get_market_snapshot_multi_cache_key(
            "BTC/USDT", "1h", "4h"
        )
        assert key == "cache:market_snapshot_multi:BTC/USDT:1h:4h"

    # Pattern Invalidation Tests
    async def test_invalidate_pattern(self, cache_service):
        """Test cache invalidation by pattern."""
        pattern = "cache:ohlcv:*"
        keys = ["cache:ohlcv:BTC/USDT:1h", "cache:ohlcv:ETH/USDT:1h"]

        cache_service.redis_client.scan = AsyncMock(
            side_effect=[
                (0, keys),  # First scan returns keys and cursor=0
            ]
        )
        cache_service.redis_client.delete = AsyncMock(return_value=2)

        result = await cache_service.invalidate_pattern(pattern)

        assert result == 2
        cache_service.redis_client.delete.assert_called_once_with(*keys)

    async def test_invalidate_pattern_multiple_scans(self, cache_service):
        """Test cache invalidation with multiple scan iterations."""
        pattern = "cache:*"
        keys1 = ["cache:key1", "cache:key2"]
        keys2 = ["cache:key3"]

        cache_service.redis_client.scan = AsyncMock(
            side_effect=[
                (100, keys1),  # First scan returns keys and cursor=100
                (0, keys2),  # Second scan returns remaining keys and cursor=0
            ]
        )
        cache_service.redis_client.delete = AsyncMock(
            side_effect=[2, 1]  # First delete returns 2, second returns 1
        )

        result = await cache_service.invalidate_pattern(pattern)

        assert result == 3
        assert cache_service.redis_client.delete.call_count == 2

    async def test_invalidate_pattern_no_keys(self, cache_service):
        """Test cache invalidation with no matching keys."""
        pattern = "cache:nonexistent:*"

        cache_service.redis_client.scan = AsyncMock(return_value=(0, []))
        cache_service.redis_client.delete = AsyncMock(return_value=0)

        result = await cache_service.invalidate_pattern(pattern)

        assert result == 0

    # Clear All Tests
    async def test_clear_all_success(self, cache_service):
        """Test clearing all cache."""
        cache_service.redis_client.flushdb = AsyncMock(return_value=True)

        result = await cache_service.clear_all()

        assert result is True
        cache_service.redis_client.flushdb.assert_called_once()

    async def test_clear_all_failure(self, cache_service):
        """Test clear all failure."""
        cache_service.redis_client.flushdb = AsyncMock(
            side_effect=Exception("Redis error")
        )

        result = await cache_service.clear_all()

        assert result is False

    # Metrics Tests
    async def test_record_hit(self, cache_service):
        """Test recording cache hit."""
        key = "test_key"
        cache_service.redis_client.incr = AsyncMock(return_value=1)
        cache_service.redis_client.expire = AsyncMock(return_value=True)

        await cache_service._record_hit(key)

        hit_key = f"metrics:cache_hits:{key}"
        cache_service.redis_client.incr.assert_called_once_with(hit_key)
        cache_service.redis_client.expire.assert_called_once()

    async def test_record_miss(self, cache_service):
        """Test recording cache miss."""
        key = "test_key"
        cache_service.redis_client.incr = AsyncMock(return_value=1)
        cache_service.redis_client.expire = AsyncMock(return_value=True)

        await cache_service._record_miss(key)

        miss_key = f"metrics:cache_misses:{key}"
        cache_service.redis_client.incr.assert_called_once_with(miss_key)
        cache_service.redis_client.expire.assert_called_once()

    async def test_get_hit_rate_with_hits_and_misses(self, cache_service):
        """Test hit rate calculation with hits and misses."""
        key = "test_key"
        cache_service.redis_client.get = AsyncMock(
            side_effect=["10", "5"]  # 10 hits, 5 misses
        )

        hit_rate = await cache_service.get_hit_rate(key)

        assert hit_rate == 10 / 15  # 66.67%

    async def test_get_hit_rate_all_hits(self, cache_service):
        """Test hit rate with all hits."""
        key = "test_key"
        cache_service.redis_client.get = AsyncMock(
            side_effect=["10", "0"]  # 10 hits, 0 misses
        )

        hit_rate = await cache_service.get_hit_rate(key)

        assert hit_rate == 1.0  # 100%

    async def test_get_hit_rate_all_misses(self, cache_service):
        """Test hit rate with all misses."""
        key = "test_key"
        cache_service.redis_client.get = AsyncMock(
            side_effect=["0", "10"]  # 0 hits, 10 misses
        )

        hit_rate = await cache_service.get_hit_rate(key)

        assert hit_rate == 0.0  # 0%

    async def test_get_hit_rate_no_metrics(self, cache_service):
        """Test hit rate with no metrics data."""
        key = "test_key"
        cache_service.redis_client.get = AsyncMock(
            side_effect=["0", "0"]  # 0 hits, 0 misses
        )

        hit_rate = await cache_service.get_hit_rate(key)

        assert hit_rate is None

    async def test_get_hit_rate_error(self, cache_service):
        """Test hit rate calculation with error."""
        key = "test_key"
        cache_service.redis_client.get = AsyncMock(
            side_effect=Exception("Redis error")
        )

        hit_rate = await cache_service.get_hit_rate(key)

        assert hit_rate is None

    # Cache Statistics Tests
    async def test_get_cache_stats(self, cache_service):
        """Test getting cache statistics."""
        hit_keys = ["metrics:cache_hits:key1", "metrics:cache_hits:key2"]
        miss_keys = ["metrics:cache_misses:key1", "metrics:cache_misses:key3"]

        async def scan_side_effect(cursor, match, count):
            if match == "metrics:cache_hits:*":
                return (0, hit_keys)
            elif match == "metrics:cache_misses:*":
                return (0, miss_keys)
            return (0, [])

        cache_service.redis_client.scan = AsyncMock(side_effect=scan_side_effect)
        cache_service.redis_client.get = AsyncMock(
            side_effect=["5", "10", "2", "3"]  # Different values for each key
        )

        stats = await cache_service.get_cache_stats()

        assert "hits" in stats
        assert "misses" in stats
        assert len(stats["hits"]) == 2
        assert len(stats["misses"]) == 2

    async def test_get_cache_stats_empty(self, cache_service):
        """Test getting cache statistics with no data."""
        async def scan_side_effect(cursor, match, count):
            return (0, [])

        cache_service.redis_client.scan = AsyncMock(side_effect=scan_side_effect)

        stats = await cache_service.get_cache_stats()

        assert stats == {"hits": {}, "misses": {}}

    # Error Handling Tests
    async def test_get_cached_with_error(self, cache_service):
        """Test get_cached error handling."""
        cache_service.redis_client.get = AsyncMock(
            side_effect=Exception("Redis connection error")
        )

        result = await cache_service.get_cached("test_key")

        assert result is None

    async def test_set_cached_with_error(self, cache_service):
        """Test set_cached error handling."""
        cache_service.redis_client.setex = AsyncMock(
            side_effect=Exception("Redis connection error")
        )

        result = await cache_service.set_cached("test_key", {"data": "test"})

        assert result is False

    async def test_delete_cached_with_error(self, cache_service):
        """Test delete_cached error handling."""
        cache_service.redis_client.delete = AsyncMock(
            side_effect=Exception("Redis connection error")
        )

        result = await cache_service.delete_cached("test_key")

        assert result is False

    # JSON Serialization Tests
    async def test_cache_complex_data_structures(self, cache_service):
        """Test caching complex data structures."""
        key = "complex_data"
        value = {
            "nested": {"deep": {"data": [1, 2, 3]}},
            "list": [1, 2, 3],
            "string": "test",
            "float": 3.14,
        }
        serialized = json.dumps(value)

        cache_service.redis_client.setex = AsyncMock(return_value=True)
        cache_service.redis_client.get = AsyncMock(return_value=serialized)

        # Set
        await cache_service.set_cached(key, value)
        assert cache_service.redis_client.setex.called

        # Get
        result = await cache_service.get_cached(key)
        assert result == value

    async def test_cache_with_default_serialization(self, cache_service):
        """Test caching data with default serialization for non-JSON types."""
        from datetime import datetime

        key = "datetime_data"
        dt = datetime(2024, 1, 1, 12, 0, 0)
        value = {"timestamp": dt}

        cache_service.redis_client.setex = AsyncMock(return_value=True)

        # Should succeed with default=str in json.dumps
        result = await cache_service.set_cached(key, value)
        assert result is True

    # Edge Cases Tests
    async def test_cache_empty_string_value(self, cache_service):
        """Test caching empty string."""
        key = "empty_string"
        value = ""
        serialized = json.dumps(value)

        cache_service.redis_client.setex = AsyncMock(return_value=True)
        cache_service.redis_client.get = AsyncMock(return_value=serialized)

        await cache_service.set_cached(key, value)
        result = await cache_service.get_cached(key)

        assert result == ""

    async def test_cache_zero_value(self, cache_service):
        """Test caching zero value."""
        key = "zero_value"
        value = 0
        serialized = json.dumps(value)

        cache_service.redis_client.setex = AsyncMock(return_value=True)
        cache_service.redis_client.get = AsyncMock(return_value=serialized)

        await cache_service.set_cached(key, value)
        result = await cache_service.get_cached(key)

        assert result == 0

    async def test_cache_false_value(self, cache_service):
        """Test caching False value."""
        key = "false_value"
        value = False
        serialized = json.dumps(value)

        cache_service.redis_client.setex = AsyncMock(return_value=True)
        cache_service.redis_client.get = AsyncMock(return_value=serialized)

        await cache_service.set_cached(key, value)
        result = await cache_service.get_cached(key)

        assert result is False

    async def test_cache_none_value(self, cache_service):
        """Test caching None value."""
        key = "none_value"
        value = None
        serialized = json.dumps(value)

        cache_service.redis_client.setex = AsyncMock(return_value=True)
        cache_service.redis_client.get = AsyncMock(return_value=serialized)

        await cache_service.set_cached(key, value)
        result = await cache_service.get_cached(key)

        assert result is None

    # Constants Validation Tests
    @pytest.mark.asyncio
    async def test_ttl_constants(self):
        """Test TTL constants are reasonable."""
        assert CacheService.TTL_MARKET_DATA == 5 * 60  # 5 minutes
        assert CacheService.TTL_OHLCV == 5 * 60  # 5 minutes
        assert CacheService.TTL_TICKER == 5 * 60  # 5 minutes
        assert CacheService.TTL_FUNDING_RATE == 5 * 60  # 5 minutes
        assert CacheService.TTL_OPEN_INTEREST == 5 * 60  # 5 minutes

    @pytest.mark.asyncio
    async def test_cache_key_constants(self):
        """Test cache key constants are defined."""
        assert CacheService.KEY_OHLCV == "cache:ohlcv:{symbol}:{timeframe}"
        assert CacheService.KEY_TICKER == "cache:ticker:{symbol}"
        assert CacheService.KEY_FUNDING_RATE == "cache:funding_rate:{symbol}"
        assert CacheService.KEY_OPEN_INTEREST == "cache:open_interest:{symbol}"
        assert CacheService.KEY_MARKET_SNAPSHOT == "cache:market_snapshot:{symbol}:{timeframe}"
        assert (
            CacheService.KEY_MARKET_SNAPSHOT_MULTI
            == "cache:market_snapshot_multi:{symbol}:{tf_short}:{tf_long}"
        )
