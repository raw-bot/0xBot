"""
Environment variable loading and validation for 0xBot configuration.

This module provides functions to load and override configuration from
environment variables with type validation and defaults.
"""

import os
from typing import Optional, Type, TypeVar, Union, Dict, Any
from decimal import Decimal

T = TypeVar("T")


def get_env(key: str, default: Optional[T] = None, type_: Type[T] = str) -> Union[T, Optional[T]]:
    """
    Get environment variable with type conversion.

    Args:
        key: Environment variable name
        default: Default value if not found
        type_: Type to convert to (str, int, float, bool, Decimal)

    Returns:
        Environment variable value converted to specified type, or default

    Raises:
        ValueError: If conversion fails and no default provided

    Example:
        >>> get_env("BOT_LOG_LEVEL", "INFO", str)
        'INFO'
        >>> get_env("MAX_BOTS", 10, int)
        10
    """
    value = os.environ.get(key)

    if value is None:
        if default is None:
            raise ValueError(f"Required environment variable not found: {key}")
        return default

    # Handle different types
    if type_ == bool:
        return value.lower() in ("true", "1", "yes", "on")  # type: ignore
    elif type_ == int:
        try:
            return int(value)  # type: ignore
        except ValueError:
            raise ValueError(f"Cannot convert {key}={value} to int")
    elif type_ == float:
        try:
            return float(value)  # type: ignore
        except ValueError:
            raise ValueError(f"Cannot convert {key}={value} to float")
    elif type_ == Decimal:
        try:
            return Decimal(value)  # type: ignore
        except Exception:
            raise ValueError(f"Cannot convert {key}={value} to Decimal")
    else:
        return value  # type: ignore


def get_env_int(key: str, default: Optional[int] = None) -> Optional[int]:
    """Get environment variable as integer."""
    try:
        return get_env(key, default, int)
    except ValueError:
        return default


def get_env_float(key: str, default: Optional[float] = None) -> Optional[float]:
    """Get environment variable as float."""
    try:
        return get_env(key, default, float)
    except ValueError:
        return default


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get environment variable as boolean."""
    try:
        return get_env(key, default, bool)
    except ValueError:
        return default


def get_env_str(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable as string."""
    return os.environ.get(key, default)


# ============================================================================
# Trading Configuration from Environment
# ============================================================================

def load_trading_config_from_env() -> Dict[str, Any]:
    """
    Load trading configuration from environment variables.

    Environment variables (all optional, use defaults if not set):
    - BOT_POSITION_SIZE_PCT: Default position size (0-1)
    - BOT_LEVERAGE: Default leverage for longs (1-10)
    - BOT_SHORT_LEVERAGE: Default leverage for shorts (1-10)
    - BOT_STOP_LOSS_PCT: Default stop loss (0-1)
    - BOT_TAKE_PROFIT_PCT: Default take profit (0-1)
    - BOT_TRADING_FEE_PCT: Trading fee percentage (0-1)
    """
    from .constants import TRADING_CONFIG

    overrides = {}

    # Position sizing
    if pos_size := get_env_float("BOT_POSITION_SIZE_PCT"):
        overrides["DEFAULT_POSITION_SIZE_PCT"] = pos_size

    if leverage := get_env_float("BOT_LEVERAGE"):
        overrides["DEFAULT_LEVERAGE"] = leverage

    if short_lev := get_env_float("BOT_SHORT_LEVERAGE"):
        overrides["SHORT_MAX_LEVERAGE"] = short_lev

    # Stop loss & take profit
    if sl := get_env_float("BOT_STOP_LOSS_PCT"):
        overrides["DEFAULT_STOP_LOSS_PCT"] = sl

    if tp := get_env_float("BOT_TAKE_PROFIT_PCT"):
        overrides["DEFAULT_TAKE_PROFIT_PCT"] = tp

    # Trading fees
    if fee := get_env_float("BOT_TRADING_FEE_PCT"):
        overrides["PAPER_TRADING_FEE_PCT"] = fee

    return {**TRADING_CONFIG, **overrides}


# ============================================================================
# Timing Configuration from Environment
# ============================================================================

def load_timing_config_from_env() -> Dict[str, Any]:
    """
    Load timing configuration from environment variables.

    Environment variables (all optional):
    - BOT_CYCLE_INTERVAL: Cycle interval in seconds (default 300)
    - BOT_NEWS_FETCH_INTERVAL: News fetch interval in seconds (default 300)
    - BOT_API_TIMEOUT: API timeout in seconds (default 5)
    """
    from .constants import TIMING_CONFIG

    overrides = {}

    if cycle := get_env_int("BOT_CYCLE_INTERVAL"):
        overrides["CYCLE_INTERVAL_SECONDS"] = cycle

    if news := get_env_int("BOT_NEWS_FETCH_INTERVAL"):
        overrides["NEWS_FETCH_INTERVAL_SECONDS"] = news

    if timeout := get_env_int("BOT_API_TIMEOUT"):
        overrides["API_TIMEOUT_SECONDS"] = timeout

    return {**TIMING_CONFIG, **overrides}


# ============================================================================
# Limits Configuration from Environment
# ============================================================================

def load_limits_config_from_env() -> Dict[str, Any]:
    """
    Load limits configuration from environment variables.

    Environment variables (all optional):
    - BOT_MAX_DRAWDOWN_PCT: Maximum drawdown (0-1)
    - BOT_MAX_TRADES_PER_DAY: Maximum trades per day
    - BOT_MAX_LEVERAGE: Maximum leverage validation
    - BOT_DAILY_LOSS_LIMIT: Daily loss circuit breaker in USD
    """
    from .constants import LIMITS_CONFIG

    overrides = {}

    if dd := get_env_float("BOT_MAX_DRAWDOWN_PCT"):
        overrides["BOT_MAX_DRAWDOWN_PCT"] = dd

    if trades := get_env_int("BOT_MAX_TRADES_PER_DAY"):
        overrides["BOT_MAX_TRADES_PER_DAY"] = trades

    if lev := get_env_float("BOT_MAX_LEVERAGE"):
        overrides["MAX_LEVERAGE_VALIDATION"] = lev

    if loss := get_env_float("BOT_DAILY_LOSS_LIMIT"):
        overrides["MAX_DAILY_LOSS_USD"] = -abs(loss)  # Ensure negative

    return {**LIMITS_CONFIG, **overrides}


# ============================================================================
# Validation Configuration from Environment
# ============================================================================

def load_validation_config_from_env() -> Dict[str, Any]:
    """
    Load validation configuration from environment variables.

    Environment variables (all optional):
    - BOT_MIN_CONFIDENCE: Minimum confidence threshold (0-1)
    - BOT_MIN_RISK_REWARD: Minimum risk/reward ratio
    - BOT_LLM_RATE_LIMIT: LLM rate limit (calls per minute)
    """
    from .constants import VALIDATION_CONFIG

    overrides = {}

    if conf := get_env_float("BOT_MIN_CONFIDENCE"):
        overrides["MIN_CONFIDENCE_ENTRY"] = conf

    if rr := get_env_float("BOT_MIN_RISK_REWARD"):
        overrides["MIN_RISK_REWARD_RATIO"] = rr

    if limit := get_env_int("BOT_LLM_RATE_LIMIT"):
        overrides["TRADE_FILTER_MIN_CONFIDENCE"] = limit

    return {**VALIDATION_CONFIG, **overrides}


# ============================================================================
# Database Configuration from Environment
# ============================================================================

def load_database_config_from_env() -> Dict[str, Any]:
    """
    Load database configuration from environment variables.

    Environment variables (all optional):
    - BOT_DB_POOL_SIZE: Connection pool size (default 20)
    - BOT_DB_MAX_OVERFLOW: Max overflow connections (default 80)
    - BOT_DB_ECHO: Echo SQL queries (default False)
    """
    from .constants import DATABASE_CONFIG

    overrides = {}

    if pool := get_env_int("BOT_DB_POOL_SIZE"):
        overrides["POOL_SIZE"] = pool

    if overflow := get_env_int("BOT_DB_MAX_OVERFLOW"):
        overrides["MAX_OVERFLOW"] = overflow

    if echo := get_env_bool("BOT_DB_ECHO"):
        overrides["ECHO_SQL"] = echo

    return {**DATABASE_CONFIG, **overrides}


# ============================================================================
# API Configuration from Environment
# ============================================================================

def load_api_config_from_env() -> Dict[str, Any]:
    """
    Load API configuration from environment variables.

    Environment variables (all optional):
    - BOT_API_RATE_LIMIT: API rate limit (requests per minute)
    """
    from .constants import API_CONFIG

    overrides = {}

    if limit := get_env_int("BOT_API_RATE_LIMIT"):
        overrides["DEFAULT_RATE_LIMIT_RPM"] = limit

    return {**API_CONFIG, **overrides}


# ============================================================================
# Complete Configuration Loading
# ============================================================================

def load_all_config_from_env() -> Dict[str, Dict[str, Any]]:
    """
    Load all configuration from environment variables.

    Returns:
        Dictionary with all configuration categories
    """
    return {
        "trading": load_trading_config_from_env(),
        "timing": load_timing_config_from_env(),
        "limits": load_limits_config_from_env(),
        "validation": load_validation_config_from_env(),
        "database": load_database_config_from_env(),
        "api": load_api_config_from_env(),
    }


def get_config_summary() -> str:
    """
    Get a human-readable summary of all loaded configuration.

    Returns:
        Formatted string with configuration summary
    """
    all_configs = load_all_config_from_env()

    lines = ["0xBot Configuration Summary", "=" * 50]

    for category, config in all_configs.items():
        lines.append(f"\n{category.upper()}:")
        for key, value in config.items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)
