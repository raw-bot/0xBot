"""Redis connection manager for caching and rate limiting."""

import os
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio import Redis


class RedisClient:
    """Redis client wrapper with connection pooling."""

    def __init__(self) -> None:
        """Initialize Redis client."""
        self._redis: Optional[Redis] = None
        self._url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    async def connect(self) -> None:
        """Establish Redis connection."""
        if self._redis is None:
            self._redis = await redis.from_url(  # type: ignore[no-untyped-call]
                self._url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10
            )

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    @property
    def client(self) -> Redis:
        """Get Redis client instance."""
        if self._redis is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._redis

    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        return await self.client.get(key)  # type: ignore[no-any-return]

    async def set(self, key: str, value: str) -> bool:
        """Set key-value pair without expiration."""
        return await self.client.set(key, value)  # type: ignore[no-any-return]

    async def set_with_ttl(self, key: str, value: str, ttl: int) -> bool:
        """Set key-value pair with TTL in seconds."""
        return await self.client.setex(key, ttl, value)  # type: ignore[no-any-return]

    async def delete(self, key: str) -> int:
        """Delete key and return number of keys deleted."""
        return await self.client.delete(key)  # type: ignore[no-any-return]

    async def increment(self, key: str) -> int:
        """Increment counter and return new value."""
        return await self.client.incr(key)  # type: ignore[no-any-return]

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time on key."""
        return await self.client.expire(key, seconds)  # type: ignore[no-any-return]

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        result: int = await self.client.exists(key)
        return result > 0

    async def ttl(self, key: str) -> int:
        """Get TTL for key (-1 if no expiration, -2 if key doesn't exist)."""
        return await self.client.ttl(key)  # type: ignore[no-any-return]


_redis_client: Optional[RedisClient] = None


async def get_redis() -> Redis:
    """Get Redis client instance (FastAPI dependency)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()
    return _redis_client.client


async def init_redis() -> None:
    """Initialize Redis connection on startup."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()
        print("Redis connected")


async def close_redis() -> None:
    """Close Redis connection on shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.disconnect()
        _redis_client = None
        print("Redis connection closed")
