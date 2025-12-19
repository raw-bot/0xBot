"""Rate limiting for LLM API calls using Redis."""

from typing import Optional

from redis.asyncio import Redis

from ..core.logger import get_logger
from ..core.redis_client import get_redis

logger = get_logger(__name__)


class RateLimiter:
    """
    Rate limiter for LLM API calls.
    
    Uses Redis to track API calls per model and enforce rate limits.
    """
    
    # Rate limits per model (requests per minute)
    RATE_LIMITS = {
        "claude-4.5-sonnet": 50,
        "gpt-4": 50,
        "deepseek-v3": 50,
        "gemini-2.5-pro": 50,
        "default": 50
    }
    
    def __init__(self, redis_client: Optional[Redis] = None):
        """
        Initialize rate limiter.
        
        Args:
            redis_client: Optional Redis client (will be created if not provided)
        """
        self.redis_client = redis_client
    
    async def _get_redis(self) -> Redis:
        """Get or create Redis client."""
        if self.redis_client is None:
            self.redis_client = await get_redis()
        return self.redis_client
    
    def _get_rate_limit(self, model: str) -> int:
        """
        Get rate limit for model.
        
        Args:
            model: Model name
            
        Returns:
            Rate limit (requests per minute)
        """
        model_lower = model.lower()
        
        for key, limit in self.RATE_LIMITS.items():
            if key in model_lower:
                return limit
        
        return self.RATE_LIMITS["default"]
    
    def _get_redis_key(self, model: str) -> str:
        """
        Get Redis key for model rate limit counter.
        
        Args:
            model: Model name
            
        Returns:
            Redis key
        """
        return f"rate_limit:{model}:count"
    
    async def check_rate_limit(self, model: str) -> bool:
        """
        Check if model has remaining API calls within rate limit.
        
        Args:
            model: Model name
            
        Returns:
            True if within limit, False if over limit
        """
        redis = await self._get_redis()
        key = self._get_redis_key(model)
        limit = self._get_rate_limit(model)
        
        # Get current count
        count = await redis.get(key)
        current_count = int(count) if count else 0
        
        if current_count >= limit:
            logger.warning(f"Rate limit exceeded for {model}: {current_count}/{limit} RPM")
            return False
        
        return True
    
    async def increment_counter(self, model: str) -> int:
        """
        Increment rate limit counter for model.
        
        Args:
            model: Model name
            
        Returns:
            New counter value
        """
        redis = await self._get_redis()
        key = self._get_redis_key(model)
        
        # Increment counter
        count = await redis.incr(key)
        
        # Set expiration if this is the first request in the window
        if count == 1:
            await redis.expire(key, 60)  # 60 seconds = 1 minute window
        
        logger.debug(f"Rate limit counter for {model}: {count}")
        return count
    
    async def track_token_usage(
        self,
        model: str,
        tokens: int,
        cost: float
    ) -> None:
        """
        Track token usage and cost for analytics.
        
        Args:
            model: Model name
            tokens: Number of tokens used
            cost: Cost in USD
        """
        redis = await self._get_redis()
        
        # Track tokens
        tokens_key = f"tokens:{model}:total"
        await redis.incrby(tokens_key, tokens)
        
        # Track cost (store as cents to avoid float precision issues)
        cost_key = f"cost:{model}:total"
        cost_cents = int(cost * 100)
        await redis.incrby(cost_key, cost_cents)
        
        logger.info(f"Tracked {tokens} tokens, ${cost:.6f} for {model}")
    
    async def get_usage_stats(self, model: str) -> dict:
        """
        Get usage statistics for model.
        
        Args:
            model: Model name
            
        Returns:
            Dict with 'tokens_used', 'total_cost', 'current_rpm'
        """
        redis = await self._get_redis()
        
        # Get tokens
        tokens_key = f"tokens:{model}:total"
        tokens = await redis.get(tokens_key)
        total_tokens = int(tokens) if tokens else 0
        
        # Get cost
        cost_key = f"cost:{model}:total"
        cost_cents = await redis.get(cost_key)
        total_cost = (int(cost_cents) / 100) if cost_cents else 0.0
        
        # Get current RPM
        count_key = self._get_redis_key(model)
        count = await redis.get(count_key)
        current_rpm = int(count) if count else 0
        
        return {
            "tokens_used": total_tokens,
            "total_cost": total_cost,
            "current_rpm": current_rpm,
            "rate_limit": self._get_rate_limit(model)
        }
    
    async def reset_usage_stats(self, model: str) -> None:
        """
        Reset usage statistics for model.
        
        Args:
            model: Model name
        """
        redis = await self._get_redis()
        
        tokens_key = f"tokens:{model}:total"
        cost_key = f"cost:{model}:total"
        
        await redis.delete(tokens_key)
        await redis.delete(cost_key)
        
        logger.info(f"Reset usage stats for {model}")


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


async def get_rate_limiter() -> RateLimiter:
    """
    Get or create rate limiter instance.
    
    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    
    if _rate_limiter is None:
        redis = await get_redis()
        _rate_limiter = RateLimiter(redis)
    
    return _rate_limiter