"""Configuration centralisée pour le bot de trading."""

import os
from decimal import Decimal
from typing import List, Optional


class TradingConfig:
    """Configuration centralisée pour le trading bot."""

    # LLM Configuration
    FORCED_MODEL_DEEPSEEK: str = os.getenv("FORCE_DEEPSEEK_MODEL", "deepseek-chat")

    # Trading Parameters (replacer les magic numbers)
    MIN_CONFIDENCE_ENTRY: float = 0.55  # 55%
    MIN_CONFIDENCE_EXIT_EARLY: float = 0.60  # 60%
    MIN_CONFIDENCE_EXIT_NORMAL: float = 0.50  # 50%

    # Position Management
    MAX_POSITION_AGE_SECONDS: int = 7200  # 2 hours
    MIN_POSITION_AGE_FOR_EXIT_SECONDS: int = 1800  # 30 minutes

    # Risk Management
    DEFAULT_STOP_LOSS_PCT: float = 0.035  # 3.5%
    DEFAULT_TAKE_PROFIT_PCT: float = 0.07  # 7%

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
            errors.append("MAX_POSITION_AGE_SECONDS must be greater than MIN_POSITION_AGE_FOR_EXIT_SECONDS")

        return len(errors) == 0, errors

    @classmethod
    def get_decimal_config(cls, key: str) -> Decimal:
        """Obtenir une configuration en Decimal."""
        return Decimal(str(getattr(cls, key, 0)))


# Instance globale
config = TradingConfig()
