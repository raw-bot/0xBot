"""Backward compatibility layer for global singleton access via DI container.

This module provides backward-compatible global functions that use the DI container
internally. Existing code can continue to use these functions, while new code should
use dependency injection via function parameters.

DEPRECATED: Use dependency injection instead of these functions in new code.
"""

from typing import Any, Optional

from .di_container import get_container


def get_redis_client() -> Any:
    """
    Get Redis client from DI container.

    DEPRECATED: Use dependency injection instead.
    """
    container = get_container()
    if not container.is_registered("redis_client"):
        from .service_factories import create_redis_client
        container.register("redis_client", create_redis_client)
    return container.get("redis_client")


async def get_redis_client_async() -> Any:
    """
    Get Redis client from DI container (async version).

    DEPRECATED: Use dependency injection instead.
    """
    container = get_container()
    if not container.is_registered("redis_client"):
        from .service_factories import create_redis_client
        container.register("redis_client", create_redis_client)
    return await container.get_async("redis_client")


def get_database_engine() -> Any:
    """
    Get database engine from DI container.

    DEPRECATED: Use dependency injection instead.
    """
    container = get_container()
    if not container.is_registered("db_engine"):
        from .service_factories import create_database_engine
        container.register("db_engine", create_database_engine)
    return container.get("db_engine")


def get_exchange_client() -> Any:
    """
    Get exchange client from DI container.

    DEPRECATED: Use dependency injection instead.
    """
    container = get_container()
    if not container.is_registered("exchange_client"):
        from .service_factories import create_exchange_client
        container.register("exchange_client", create_exchange_client)
    return container.get("exchange_client")


def get_llm_client() -> Any:
    """
    Get LLM client from DI container.

    DEPRECATED: Use dependency injection instead.
    """
    container = get_container()
    if not container.is_registered("llm_client"):
        from .service_factories import create_llm_client
        container.register("llm_client", create_llm_client)
    return container.get("llm_client")


def get_config() -> Any:
    """
    Get config from DI container.

    DEPRECATED: Use dependency injection instead.
    """
    container = get_container()
    if not container.is_registered("config"):
        from .service_factories import create_config
        container.register("config", create_config)
    return container.get("config")


def get_logger(name: str) -> Any:
    """
    Get logger from DI container.

    DEPRECATED: Use dependency injection instead.
    """
    container = get_container()
    logger_key = f"logger_{name}"
    if not container.is_registered(logger_key):
        from .service_factories import create_logger
        from functools import partial
        container.register(logger_key, partial(create_logger, name))
    return container.get(logger_key)


def get_rate_limiter() -> Any:
    """
    Get rate limiter from DI container.

    DEPRECATED: Use dependency injection instead.
    """
    container = get_container()
    if not container.is_registered("rate_limiter"):
        from .service_factories import create_rate_limiter
        container.register("rate_limiter", create_rate_limiter)
    return container.get("rate_limiter")


def get_query_profiler() -> Any:
    """
    Get query profiler from DI container.

    DEPRECATED: Use dependency injection instead.
    """
    container = get_container()
    if not container.is_registered("query_profiler"):
        from .service_factories import create_query_profiler
        container.register("query_profiler", create_query_profiler)
    return container.get("query_profiler")


def get_market_sentiment_service() -> Any:
    """
    Get market sentiment service from DI container.

    DEPRECATED: Use dependency injection instead.
    """
    container = get_container()
    if not container.is_registered("market_sentiment_service"):
        from .service_factories import create_market_sentiment_service
        container.register("market_sentiment_service", create_market_sentiment_service)
    return container.get("market_sentiment_service")


def get_fvg_detector_service() -> Any:
    """
    Get FVG detector service from DI container.

    DEPRECATED: Use dependency injection instead.
    """
    container = get_container()
    if not container.is_registered("fvg_detector"):
        from .service_factories import create_fvg_detector_service
        container.register("fvg_detector", create_fvg_detector_service)
    return container.get("fvg_detector")


def get_cache_service() -> Any:
    """
    Get cache service from DI container.

    DEPRECATED: Use dependency injection instead.
    """
    container = get_container()
    if not container.is_registered("cache_service"):
        from .service_factories import create_cache_service
        container.register("cache_service", create_cache_service)
    return container.get("cache_service")


def get_market_data_service() -> Any:
    """
    Get market data service from DI container.

    DEPRECATED: Use dependency injection instead.
    """
    container = get_container()
    if not container.is_registered("market_data_service"):
        from .service_factories import create_market_data_service
        container.register("market_data_service", create_market_data_service)
    return container.get("market_data_service")


def get_multi_coin_prompt_service() -> Any:
    """
    Get multi-coin prompt service from DI container.

    DEPRECATED: Use dependency injection instead.
    """
    container = get_container()
    if not container.is_registered("multi_coin_prompt_service"):
        from .service_factories import create_multi_coin_prompt_service
        container.register("multi_coin_prompt_service", create_multi_coin_prompt_service)
    return container.get("multi_coin_prompt_service")
