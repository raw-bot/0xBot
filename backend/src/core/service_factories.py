"""Factory functions for creating service instances with dependency injection."""

import os
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .config import config
from .database import AsyncSessionLocal, engine
from .exchange_client import ExchangeClient
from .llm_client import LLMClient, get_llm_client
from .logger import get_logger
from .query_profiler import QueryProfiler
from .rate_limiter import RateLimiter
from .redis_client import RedisClient


def create_redis_client() -> RedisClient:
    """Factory for Redis client singleton."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    return RedisClient()


def create_database_session_maker() -> async_sessionmaker:
    """Factory for database session maker."""
    return AsyncSessionLocal


async def create_database_session() -> AsyncSession:
    """Factory for individual database sessions."""
    async with AsyncSessionLocal() as session:
        return session


def create_exchange_client() -> ExchangeClient:
    """Factory for exchange client singleton."""
    paper_trading = os.getenv("PAPER_TRADING", "true").lower() == "true"
    return ExchangeClient(paper_trading=paper_trading)


def create_llm_client() -> LLMClient:
    """Factory for LLM client singleton."""
    return LLMClient()


def create_config() -> Any:
    """Factory for configuration singleton."""
    return config


def create_logger(name: str) -> Any:
    """Factory for logger instances."""
    return get_logger(name)


def create_rate_limiter() -> RateLimiter:
    """Factory for rate limiter singleton."""
    calls_per_minute = getattr(config, "LLM_CALLS_PER_MINUTE", 10)
    return RateLimiter(calls_per_minute=calls_per_minute)


def create_query_profiler() -> QueryProfiler:
    """Factory for query profiler singleton."""
    return QueryProfiler()


def create_database_engine() -> Any:
    """Factory for database engine singleton."""
    return engine
