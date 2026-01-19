"""Configuration centralisee pour le bot de trading."""

import os
from decimal import Decimal
from pathlib import Path
from typing import List

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=env_path)


class TradingConfig:
    """Configuration centralisee pour le trading bot."""

    # LLM Configuration
    FORCED_MODEL_DEEPSEEK: str = os.getenv("FORCE_DEEPSEEK_MODEL", "deepseek-chat")

    # News API
    CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY", "")
    NEWS_FETCH_INTERVAL: int = 300

    # Trading Parameters
    MIN_CONFIDENCE_ENTRY: float = 0.70
    MIN_CONFIDENCE_EXIT_EARLY: float = 0.60
    MIN_CONFIDENCE_EXIT_NORMAL: float = 0.70
    MAX_NEW_ENTRIES_PER_CYCLE: int = 2

    # Risk Management
    DEFAULT_STOP_LOSS_PCT: float = 0.035
    DEFAULT_TAKE_PROFIT_PCT: float = 0.08
    DEFAULT_POSITION_SIZE_PCT: float = 0.35
    DEFAULT_LEVERAGE: float = 5.0

    # SHORT-specific settings
    SHORT_MAX_LEVERAGE: float = 3.0
    SHORT_MIN_CONFIDENCE: float = 0.65
    SHORT_POSITION_SIZE_PCT: float = 0.25

    # Trading Fees (Binance Futures Taker)
    PAPER_TRADING_FEE_PCT: float = 0.0005

    # Allowed symbols whitelist
    ALLOWED_SYMBOLS: List[str] = [
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "BNB/USDT",
        "XRP/USDT",
    ]

    # Rate Limiting
    LLM_CALLS_PER_MINUTE: int = 10

    # Performance
    CYCLE_INTERVAL_SECONDS: int = 300

    # Database Connection Pool
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))  # Concurrent connections
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "80"))  # Queue overflow before blocking
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # Recycle connections after 1 hour
    DB_POOL_PRE_PING: bool = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"  # Check connection before use

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
