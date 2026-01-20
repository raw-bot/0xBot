"""Rate limiting for LLM API calls using Redis."""

from typing import Optional

from redis.asyncio import Redis

from ..core.logger import get_logger
from ..core.redis_client import get_redis

logger = get_logger(__name__)


# Rate limits per model (requests per minute)
DEFAULT_RATE_LIMIT = 50
MODEL_RATE_LIMITS = {
    "claude-4.5-sonnet": 50,
    "gpt-4": 50,
    "deepseek-v3": 50,
    "gemini-2.5-pro": 50,
}


class RateLimiter:
    """Rate limiter for LLM API calls using Redis."""

    def __init__(self, redis_client: Optional[Redis] = None):
        """Initialize rate limiter."""
        self.redis_client = redis_client

    async def _get_redis(self) -> Redis:
        """Get or create Redis client."""
        if self.redis_client is None:
            self.redis_client = await get_redis()
        return self.redis_client

    def _get_rate_limit(self, model: str) -> int:
        """Get rate limit for model."""
        model_lower = model.lower()
        for key, limit in MODEL_RATE_LIMITS.items():
            if key in model_lower:
                return limit
        return DEFAULT_RATE_LIMIT

    async def check_rate_limit(self, model: str) -> bool:
        """Check if model has remaining API calls within rate limit."""
        redis = await self._get_redis()
        key = f"rate_limit:{model}:count"
        limit = self._get_rate_limit(model)

        count = await redis.get(key)
        current_count = int(count) if count else 0

        if current_count >= limit:
            logger.warning(f"Rate limit exceeded for {model}: {current_count}/{limit} RPM")
            return False
        return True

    async def increment_counter(self, model: str) -> int:
        """Increment rate limit counter for model."""
        redis = await self._get_redis()
        key = f"rate_limit:{model}:count"

        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)

        logger.debug(f"Rate limit counter for {model}: {count}")
        return int(count) if count is not None else 0

    async def track_token_usage(self, model: str, tokens: int, cost: float) -> None:
        """Track token usage and cost for analytics."""
        redis = await self._get_redis()

        await redis.incrby(f"tokens:{model}:total", tokens)
        await redis.incrby(f"cost:{model}:total", int(cost * 100))

        logger.info(f"Tracked {tokens} tokens, ${cost:.6f} for {model}")

    async def get_usage_stats(self, model: str) -> dict[str, object]:
        """Get usage statistics for model."""
        redis = await self._get_redis()

        tokens = await redis.get(f"tokens:{model}:total")
        cost_cents = await redis.get(f"cost:{model}:total")
        count = await redis.get(f"rate_limit:{model}:count")

        return {
            "tokens_used": int(tokens) if tokens else 0,
            "total_cost": (int(cost_cents) / 100) if cost_cents else 0.0,
            "current_rpm": int(count) if count else 0,
            "rate_limit": self._get_rate_limit(model),
        }

    async def reset_usage_stats(self, model: str) -> None:
        """Reset usage statistics for model."""
        redis = await self._get_redis()
        await redis.delete(f"tokens:{model}:total")
        await redis.delete(f"cost:{model}:total")
        logger.info(f"Reset usage stats for {model}")


_rate_limiter: Optional[RateLimiter] = None


async def get_rate_limiter() -> RateLimiter:
    """Get or create rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        redis = await get_redis()
        _rate_limiter = RateLimiter(redis)
    return _rate_limiter
