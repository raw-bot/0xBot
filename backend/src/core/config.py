"""
Configuration centralisee pour le bot de trading.

This module provides backward-compatible access to configuration values
while centralizing all constants in config.constants module.
"""

import os
from decimal import Decimal
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Import from new config package for centralized constants
from ..config import (
    TRADING_CONFIG,
    TIMING_CONFIG,
    LIMITS_CONFIG,
    VALIDATION_CONFIG,
    DATABASE_CONFIG,
    API_CONFIG,
    get_constant,
)

env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=env_path)


class TradingConfig:
    """Configuration centralisee pour le trading bot.

    This class provides backward-compatible access to configuration.
    All constants are now centralized in config.constants and can be
    overridden via environment variables using config.environment.
    """

    # LLM Configuration
    FORCED_MODEL_DEEPSEEK: str = os.getenv("FORCE_DEEPSEEK_MODEL", "deepseek-chat")

    # News API
    CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY", "")

    # Trading Parameters - loaded from config package
    NEWS_FETCH_INTERVAL: int = TIMING_CONFIG["NEWS_FETCH_INTERVAL_SECONDS"]
    MIN_CONFIDENCE_ENTRY: float = VALIDATION_CONFIG["MIN_CONFIDENCE_ENTRY"]
    MIN_CONFIDENCE_EXIT_EARLY: float = VALIDATION_CONFIG["MIN_CONFIDENCE_EXIT_EARLY"]
    MIN_CONFIDENCE_EXIT_NORMAL: float = VALIDATION_CONFIG["MIN_CONFIDENCE_EXIT_NORMAL"]
    MAX_NEW_ENTRIES_PER_CYCLE: int = LIMITS_CONFIG["MAX_NEW_ENTRIES_PER_CYCLE"]

    # Risk Management - loaded from config package
    DEFAULT_STOP_LOSS_PCT: float = TRADING_CONFIG["DEFAULT_STOP_LOSS_PCT"]
    DEFAULT_TAKE_PROFIT_PCT: float = TRADING_CONFIG["DEFAULT_TAKE_PROFIT_PCT"]
    DEFAULT_POSITION_SIZE_PCT: float = TRADING_CONFIG["DEFAULT_POSITION_SIZE_PCT"]
    DEFAULT_LEVERAGE: float = TRADING_CONFIG["DEFAULT_LEVERAGE"]

    # SHORT-specific settings - loaded from config package
    SHORT_MAX_LEVERAGE: float = TRADING_CONFIG["SHORT_MAX_LEVERAGE"]
    SHORT_MIN_CONFIDENCE: float = VALIDATION_CONFIG["SHORT_MIN_CONFIDENCE"]
    SHORT_POSITION_SIZE_PCT: float = TRADING_CONFIG["SHORT_POSITION_SIZE_PCT"]

    # Trading Fees - loaded from config package
    PAPER_TRADING_FEE_PCT: float = TRADING_CONFIG["PAPER_TRADING_FEE_PCT"]

    # Allowed symbols whitelist
    ALLOWED_SYMBOLS: List[str] = [
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "BNB/USDT",
        "XRP/USDT",
    ]

    # Rate Limiting - loaded from config package
    LLM_CALLS_PER_MINUTE: int = API_CONFIG["LLM_CALLS_PER_MINUTE"]

    # Performance - loaded from config package
    CYCLE_INTERVAL_SECONDS: int = TIMING_CONFIG["CYCLE_INTERVAL_SECONDS"]

    # Database Connection Pool - loaded from config package with env overrides
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", str(DATABASE_CONFIG["POOL_SIZE"])))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", str(DATABASE_CONFIG["MAX_OVERFLOW"])))
    DB_POOL_RECYCLE: int = TIMING_CONFIG["DB_POOL_RECYCLE_SECONDS"]
    DB_POOL_PRE_PING: bool = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"

    @classmethod
    def validate_config(cls) -> tuple[bool, List[str]]:
        """Validate configuration values."""
        errors = []

        if not 0 < cls.MIN_CONFIDENCE_ENTRY < 1:
            errors.append("MIN_CONFIDENCE_ENTRY must be between 0 and 1")

        if not 0 < cls.DEFAULT_STOP_LOSS_PCT < 1:
            errors.append("DEFAULT_STOP_LOSS_PCT must be between 0 and 1")

        if not 0 < cls.DEFAULT_TAKE_PROFIT_PCT < 1:
            errors.append("DEFAULT_TAKE_PROFIT_PCT must be between 0 and 1")

        return len(errors) == 0, errors

    @classmethod
    def get_decimal_config(cls, key: str) -> Decimal:
        """Get a configuration value as Decimal."""
        return Decimal(str(getattr(cls, key, 0)))


config = TradingConfig()
