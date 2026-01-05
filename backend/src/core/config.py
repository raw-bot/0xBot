"""Configuration centralisée pour le bot de trading."""

import os
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Load .env from the backend directory (project root)
env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=env_path)


class TradingConfig:
    """Configuration centralisée pour le trading bot."""

    # LLM Configuration
    FORCED_MODEL_DEEPSEEK: str = os.getenv("FORCE_DEEPSEEK_MODEL", "deepseek-chat")

    # News API (CryptoCompare)
    CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY", "")
    NEWS_FETCH_INTERVAL: int = 300  # 5 minutes (aligned with cycle)

    # Trading Parameters (replacer les magic numbers)
    MIN_CONFIDENCE_ENTRY: float = 0.70  # 70% (NoF1 reference threshold)
    MIN_CONFIDENCE_EXIT_EARLY: float = 0.60  # 60%
    MIN_CONFIDENCE_EXIT_NORMAL: float = 0.70  # 70% - raised to prevent premature exits

    # Smart Exit Protection - Prevents micro-profit exits
    # Exit is ALWAYS allowed if position is losing (protection mode)
    # Exit only allowed if PnL >= this threshold when position is profitable
    MIN_PNL_PCT_FOR_PROFIT_EXIT: float = 1.5  # 1.5% min profit to exit (or use SL/TP)

    # Position Management
    MAX_POSITION_AGE_SECONDS: int = 7200  # 2 hours
    MIN_POSITION_AGE_FOR_EXIT_SECONDS: int = 3600  # 1 hour - more time to develop

    # Risk Management - Optimized for better R/R
    DEFAULT_STOP_LOSS_PCT: float = 0.03  # 3% SL
    DEFAULT_TAKE_PROFIT_PCT: float = 0.06  # 6% TP
    DEFAULT_POSITION_SIZE_PCT: float = 0.25  # 25% position
    DEFAULT_LEVERAGE: float = 5.0  # 5x Leverage for LONG

    # SHORT-specific settings (safer due to unlimited loss potential)
    SHORT_MAX_LEVERAGE: float = 3.0  # 3x max for SHORT
    SHORT_MIN_CONFIDENCE: float = 0.65  # Lower threshold
    SHORT_POSITION_SIZE_PCT: float = 0.15  # Smaller size

    # Trading Fees (Binance Futures Taker fee)
    PAPER_TRADING_FEE_PCT: float = 0.0005  # 0.05% per trade (real Binance rate)

    # Security: Allowed trading symbols whitelist (majors only)
    ALLOWED_SYMBOLS: List[str] = [
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "BNB/USDT",
        "XRP/USDT",
    ]

    # Rate Limiting
    LLM_CALLS_PER_MINUTE: int = 10  # Max LLM API calls per minute

    # Performance
    CYCLE_INTERVAL_SECONDS: int = 300  # 5 minutes

    @classmethod
    def validate_config(cls) -> tuple[bool, List[str]]:
        """Valide la configuration actuelle."""
        errors = []

        # Valider les pourcentages
        if not 0 < cls.MIN_CONFIDENCE_ENTRY < 1:
            errors.append("MIN_CONFIDENCE_ENTRY must be between 0 and 1")

        if not 0 < cls.DEFAULT_STOP_LOSS_PCT < 1:
            errors.append("DEFAULT_STOP_LOSS_PCT must be between 0 and 1")

        if not 0 < cls.DEFAULT_TAKE_PROFIT_PCT < 1:
            errors.append("DEFAULT_TAKE_PROFIT_PCT must be between 0 and 1")

        # Valider les temps
        if cls.MIN_POSITION_AGE_FOR_EXIT_SECONDS < 0:
            errors.append("MIN_POSITION_AGE_FOR_EXIT_SECONDS must be positive")

        if cls.MAX_POSITION_AGE_SECONDS <= cls.MIN_POSITION_AGE_FOR_EXIT_SECONDS:
            errors.append(
                "MAX_POSITION_AGE_SECONDS must be greater than MIN_POSITION_AGE_FOR_EXIT_SECONDS"
            )

        return len(errors) == 0, errors

    @classmethod
    def get_decimal_config(cls, key: str) -> Decimal:
        """Obtenir une configuration en Decimal."""
        return Decimal(str(getattr(cls, key, 0)))


# Instance globale
config = TradingConfig()
