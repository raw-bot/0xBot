"""Business logic services for the trading platform."""

from .bot_service import BotCreate, BotService, BotUpdate
from .indicator_service import IndicatorService
from .indicator_strategy_service import IndicatorStrategyService, SignalType, IndicatorSignal
from .kelly_position_sizing_service import KellyPositionSizingService
from .multi_coin_prompt_service import MultiCoinPromptService
from .market_data_service import OHLCV, MarketDataService, Ticker
from .position_service import PositionOpen, PositionService
from .risk_manager_service import RiskManagerService
from .trade_executor_service import TradeExecutorService
from .trading_engine_service import TradingEngine
from .strategy_performance_service import StrategyPerformanceService, StrategyMetrics
from .trade_filter_service import TradeFilterService
from .trading_memory_service import TradingMemoryService

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

    # NEW: Indicator-based strategy (replaces LLM)
    'IndicatorStrategyService',
    'SignalType',
    'IndicatorSignal',

    # NEW: Kelly position sizing
    'KellyPositionSizingService',

    # Multi-coin LLM prompt service (remplace LLMPromptService archivé)
    'MultiCoinPromptService',

    # Trade executor service
    'TradeExecutorService',

    # Risk manager service
    'RiskManagerService',

    # Trading engine
    'TradingEngine',

    # NEW: Strategy performance tracking
    'StrategyPerformanceService',
    'StrategyMetrics',

    # NEW: Trade filtering and profitability validation
    'TradeFilterService',

    # NEW: Trading memory (DeepMem integration)
    'TradingMemoryService',
]
