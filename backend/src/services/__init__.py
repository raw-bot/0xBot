"""Business logic services for the trading platform."""

from .bot_service import BotCreate, BotService, BotUpdate
from .indicator_service import IndicatorService
from .multi_coin_prompt_service import MultiCoinPromptService
from .market_data_service import OHLCV, MarketDataService, Ticker
from .position_service import PositionOpen, PositionService
from .risk_manager_service import RiskManagerService
from .trade_executor_service import TradeExecutorService
from .trading_engine_service import TradingEngine

__all__ = [
    # Bot service
    'BotService',
    'BotCreate',
    'BotUpdate',

    # Position service
    'PositionService',
    'PositionOpen',

    # Market data service
    'MarketDataService',
    'OHLCV',
    'Ticker',

    # Indicator service
    'IndicatorService',

    # Multi-coin LLM prompt service (remplace LLMPromptService archivé)
    'MultiCoinPromptService',

    # Trade executor service
    'TradeExecutorService',

    # Risk manager service
    'RiskManagerService',

    # Trading engine
    'TradingEngine',
]
