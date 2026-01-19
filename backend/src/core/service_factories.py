"""Factory functions for creating service instances with dependency injection."""

import os
from typing import Any, Optional

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


def create_market_sentiment_service() -> Any:
    """Factory for market sentiment service singleton."""
    from ..services.market_sentiment_service import MarketSentimentService
    return MarketSentimentService()


def create_fvg_detector_service() -> Any:
    """Factory for FVG detector service singleton."""
    from ..services.fvg_detector_service import FVGDetectorService
    return FVGDetectorService()


def create_cache_service() -> Any:
    """Factory for cache service singleton."""
    from ..services.cache_service import CacheService
    redis_client = create_redis_client()
    return CacheService(redis_client)


def create_market_data_service() -> Any:
    """Factory for market data service singleton."""
    from ..services.market_data_service import MarketDataService
    exchange_client = create_exchange_client()
    cache_service = create_cache_service()
    return MarketDataService(exchange_client=exchange_client, cache_service=cache_service)


def create_multi_coin_prompt_service() -> Any:
    """Factory for multi-coin prompt service singleton."""
    from ..services.multi_coin_prompt.service import MultiCoinPromptService
    sentiment_service = create_market_sentiment_service()
    fvg_detector = create_fvg_detector_service()
    return MultiCoinPromptService(sentiment_service=sentiment_service, fvg_detector=fvg_detector)


def create_trading_cycle_manager(
    bot: Any,
    db: AsyncSession,
    llm_client: Optional[LLMClient] = None,
    sentiment_service: Optional[Any] = None,
    market_data_service: Optional[Any] = None,
    prompt_service: Optional[Any] = None,
    trading_memory: Optional[Any] = None,
) -> Any:
    """Factory for trading cycle manager with dependency injection."""
    from ..services.trading_engine.cycle_manager import TradingCycleManager
    from ..services.trading_memory_service import TradingMemoryService

    llm_client = llm_client or create_llm_client()
    sentiment_service = sentiment_service or create_market_sentiment_service()
    market_data_service = market_data_service or create_market_data_service()
    prompt_service = prompt_service or create_multi_coin_prompt_service()
    trading_memory = trading_memory or TradingMemoryService(bot.id)

    return TradingCycleManager(
        bot=bot,
        db=db,
        llm_client=llm_client,
        sentiment_service=sentiment_service,
        market_data_service=market_data_service,
        prompt_service=prompt_service,
        trading_memory=trading_memory,
    )
