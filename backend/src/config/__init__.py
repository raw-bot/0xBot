"""
Configuration package for 0xBot.

This package provides centralized configuration management through:
1. constants.py - All configuration constants organized by category
2. environment.py - Environment variable loading with type validation
3. This __init__.py - Single import point for all configuration

Usage:
    # Import specific constants
    from src.config import TRADING_CONFIG, LIMITS_CONFIG

    # Import helper functions
    from src.config import get_constant, get_config

    # Import environment loaders
    from src.config import load_all_config_from_env, get_env_float
"""

# Export all constants
from .constants import (
    TRADING_CONFIG,
    TIMING_CONFIG,
    LIMITS_CONFIG,
    VALIDATION_CONFIG,
    DATABASE_CONFIG,
    API_CONFIG,
    INDICATOR_CONFIG,
    KELLY_CONFIG,
    PERFORMANCE_CONFIG,
    PROMPT_CONFIG,
    get_config,
    get_constant,
)

# Export environment loaders
from .environment import (
    get_env,
    get_env_int,
    get_env_float,
    get_env_bool,
    get_env_str,
    load_trading_config_from_env,
    load_timing_config_from_env,
    load_limits_config_from_env,
    load_validation_config_from_env,
    load_database_config_from_env,
    load_api_config_from_env,
    load_all_config_from_env,
    get_config_summary,
)

__all__ = [
    # Constants
    "TRADING_CONFIG",
    "TIMING_CONFIG",
    "LIMITS_CONFIG",
    "VALIDATION_CONFIG",
    "DATABASE_CONFIG",
    "API_CONFIG",
    "INDICATOR_CONFIG",
    "KELLY_CONFIG",
    "PERFORMANCE_CONFIG",
    "PROMPT_CONFIG",
    # Helper functions for constants
    "get_config",
    "get_constant",
    # Environment functions
    "get_env",
    "get_env_int",
    "get_env_float",
    "get_env_bool",
    "get_env_str",
    "load_trading_config_from_env",
    "load_timing_config_from_env",
    "load_limits_config_from_env",
    "load_validation_config_from_env",
    "load_database_config_from_env",
    "load_api_config_from_env",
    "load_all_config_from_env",
    "get_config_summary",
]
