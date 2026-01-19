"""Caching service for market data and expensive operations."""

import json
from typing import Any, Optional

from redis.asyncio import Redis

from ..core.logger import get_logger
from ..core.redis_client import get_redis

logger = get_logger(__name__)


class CacheService:
    """Service for caching expensive operations with TTL support."""

    # Cache TTL constants (in seconds)
    TTL_MARKET_DATA = 5 * 60  # 5 minutes for market data
    TTL_OHLCV = 5 * 60  # 5 minutes for OHLCV data
    TTL_TICKER = 5 * 60  # 5 minutes for ticker data
    TTL_FUNDING_RATE = 5 * 60  # 5 minutes for funding rates
    TTL_OPEN_INTEREST = 5 * 60  # 5 minutes for open interest
    TTL_INDICATOR = 15 * 60  # 15 minutes for technical indicators

    # Cache keys
    KEY_OHLCV = "cache:ohlcv:{symbol}:{timeframe}"
    KEY_TICKER = "cache:ticker:{symbol}"
    KEY_FUNDING_RATE = "cache:funding_rate:{symbol}"
    KEY_OPEN_INTEREST = "cache:open_interest:{symbol}"
    KEY_MARKET_SNAPSHOT = "cache:market_snapshot:{symbol}:{timeframe}"
    KEY_MARKET_SNAPSHOT_MULTI = "cache:market_snapshot_multi:{symbol}:{tf_short}:{tf_long}"
    KEY_INDICATOR_SMA = "cache:indicator:sma:{symbol}:{timeframe}:{period}"
    KEY_INDICATOR_EMA = "cache:indicator:ema:{symbol}:{timeframe}:{period}"
    KEY_INDICATOR_RSI = "cache:indicator:rsi:{symbol}:{timeframe}:{period}"
    KEY_INDICATOR_MACD = "cache:indicator:macd:{symbol}:{timeframe}"

    # Metrics keys
    KEY_CACHE_HITS = "metrics:cache_hits:{key}"
    KEY_CACHE_MISSES = "metrics:cache_misses:{key}"

    def __init__(self, redis_client: Optional[Redis] = None):
        """Initialize cache service with Redis client."""
        self.redis_client = redis_client

    async def _get_redis(self) -> Redis:
        """Get Redis client instance."""
        if self.redis_client is None:
            self.redis_client = await get_redis()
        return self.redis_client

    async def get_cached(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value (deserialized from JSON) or None if not found
        """
        try:
            redis = await self._get_redis()
            value = await redis.get(key)

            if value:
                await self._record_hit(key)
                return json.loads(value)

            await self._record_miss(key)
            return None
        except Exception as e:
            logger.error(f"Error retrieving from cache (key={key}): {e}")
            return None

    async def set_cached(
        self, key: str, value: Any, ttl: int = TTL_MARKET_DATA
    ) -> bool:
        """Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (default 5 minutes)

        Returns:
            True if successfully set, False otherwise
        """
        try:
            redis = await self._get_redis()
            serialized = json.dumps(value, default=str)
            result = await redis.setex(key, ttl, serialized)
            logger.debug(f"Cache set (key={key}, ttl={ttl}s)")
            return bool(result)
        except Exception as e:
            logger.error(f"Error setting cache (key={key}): {e}")
            return False

    async def delete_cached(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if key didn't exist
        """
        try:
            redis = await self._get_redis()
            deleted = await redis.delete(key)
            logger.debug(f"Cache deleted (key={key}, deleted={deleted})")
            return bool(deleted)
        except Exception as e:
            logger.error(f"Error deleting cache (key={key}): {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all cache keys matching a pattern.

        Args:
            pattern: Redis key pattern (e.g., 'cache:ohlcv:*')

        Returns:
            Number of keys deleted
        """
        try:
            redis = await self._get_redis()
            # Use SCAN to avoid blocking on large keyspaces
            cursor = 0
            count = 0
            while True:
                cursor, keys = await redis.scan(cursor, match=pattern, count=100)
                if keys:
                    count += await redis.delete(*keys)
                if cursor == 0:
                    break
            logger.debug(f"Cache invalidated (pattern={pattern}, deleted={count})")
            return count
        except Exception as e:
            logger.error(f"Error invalidating cache pattern (pattern={pattern}): {e}")
            return 0

    async def clear_all(self) -> bool:
        """Clear all cache keys (use with caution).

        Returns:
            True if successful
        """
        try:
            redis = await self._get_redis()
            await redis.flushdb()
            logger.warning("All cache cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing all cache: {e}")
            return False

    async def get_ohlcv_cache_key(self, symbol: str, timeframe: str) -> str:
        """Get OHLCV cache key."""
        return self.KEY_OHLCV.format(symbol=symbol, timeframe=timeframe)

    async def get_ticker_cache_key(self, symbol: str) -> str:
        """Get ticker cache key."""
        return self.KEY_TICKER.format(symbol=symbol)

    async def get_funding_rate_cache_key(self, symbol: str) -> str:
        """Get funding rate cache key."""
        return self.KEY_FUNDING_RATE.format(symbol=symbol)

    async def get_open_interest_cache_key(self, symbol: str) -> str:
        """Get open interest cache key."""
        return self.KEY_OPEN_INTEREST.format(symbol=symbol)

    async def get_market_snapshot_cache_key(self, symbol: str, timeframe: str) -> str:
        """Get market snapshot cache key."""
        return self.KEY_MARKET_SNAPSHOT.format(symbol=symbol, timeframe=timeframe)

    async def get_market_snapshot_multi_cache_key(
        self, symbol: str, tf_short: str, tf_long: str
    ) -> str:
        """Get multi-timeframe market snapshot cache key."""
        return self.KEY_MARKET_SNAPSHOT_MULTI.format(
            symbol=symbol, tf_short=tf_short, tf_long=tf_long
        )

    async def get_sma_cache_key(self, symbol: str, timeframe: str, period: int) -> str:
        """Get SMA cache key."""
        return self.KEY_INDICATOR_SMA.format(symbol=symbol, timeframe=timeframe, period=period)

    async def get_ema_cache_key(self, symbol: str, timeframe: str, period: int) -> str:
        """Get EMA cache key."""
        return self.KEY_INDICATOR_EMA.format(symbol=symbol, timeframe=timeframe, period=period)

    async def get_rsi_cache_key(self, symbol: str, timeframe: str, period: int) -> str:
        """Get RSI cache key."""
        return self.KEY_INDICATOR_RSI.format(symbol=symbol, timeframe=timeframe, period=period)

    async def get_macd_cache_key(self, symbol: str, timeframe: str) -> str:
        """Get MACD cache key."""
        return self.KEY_INDICATOR_MACD.format(symbol=symbol, timeframe=timeframe)

    async def _record_hit(self, key: str) -> None:
        """Record cache hit metric."""
        try:
            redis = await self._get_redis()
            hit_key = self.KEY_CACHE_HITS.format(key=key)
            await redis.incr(hit_key)
            await redis.expire(hit_key, 3600)  # Keep metrics for 1 hour
        except Exception as e:
            logger.error(f"Error recording cache hit: {e}")

    async def _record_miss(self, key: str) -> None:
        """Record cache miss metric."""
        try:
            redis = await self._get_redis()
            miss_key = self.KEY_CACHE_MISSES.format(key=key)
            await redis.incr(miss_key)
            await redis.expire(miss_key, 3600)  # Keep metrics for 1 hour
        except Exception as e:
            logger.error(f"Error recording cache miss: {e}")

    async def get_hit_rate(self, key: str) -> Optional[float]:
        """Get cache hit rate for a key (hit_rate = hits / (hits + misses)).

        Args:
            key: Cache key

        Returns:
            Hit rate as float (0.0 to 1.0) or None if no metrics
        """
        try:
            redis = await self._get_redis()
            hit_key = self.KEY_CACHE_HITS.format(key=key)
            miss_key = self.KEY_CACHE_MISSES.format(key=key)

            hits = int(await redis.get(hit_key) or 0)
            misses = int(await redis.get(miss_key) or 0)

            total = hits + misses
            if total == 0:
                return None

            return hits / total
        except Exception as e:
            logger.error(f"Error calculating hit rate: {e}")
            return None

    async def get_cache_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache hit/miss counts for all tracked keys
        """
        try:
            redis = await self._get_redis()
            stats = {"hits": {}, "misses": {}}

            # Scan for hit metrics
            cursor = 0
            while True:
                cursor, keys = await redis.scan(
                    cursor, match="metrics:cache_hits:*", count=100
                )
                for key in keys:
                    cache_key = key.replace("metrics:cache_hits:", "")
                    value = await redis.get(key)
                    stats["hits"][cache_key] = int(value or 0)
                if cursor == 0:
                    break

            # Scan for miss metrics
            cursor = 0
            while True:
                cursor, keys = await redis.scan(
                    cursor, match="metrics:cache_misses:*", count=100
                )
                for key in keys:
                    cache_key = key.replace("metrics:cache_misses:", "")
                    value = await redis.get(key)
                    stats["misses"][cache_key] = int(value or 0)
                if cursor == 0:
                    break

            return stats
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"hits": {}, "misses": {}}


# Singleton instance
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """Get cache service instance (FastAPI dependency)."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
