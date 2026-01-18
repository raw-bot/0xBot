"""Trading Blocks - Modular components for the trading engine.

Each block is responsible for a single concern:
- block_market_data: Fetch prices and indicators
- block_portfolio: Portfolio state and equity
- block_indicator_decision: Indicator-based trading signals (replaces LLM)
- block_llm_decision: LLM calls and decision parsing (deprecated)
- block_risk: Risk validation
- block_execution: Trade execution
"""

from .block_execution import ExecutionBlock
from .block_indicator_decision import IndicatorDecisionBlock
from .block_llm_decision import LLMDecisionBlock
from .block_market_data import MarketDataBlock
from .block_portfolio import PortfolioBlock
from .block_risk import RiskBlock
from .orchestrator import TradingOrchestrator

__all__ = [
    "MarketDataBlock",
    "PortfolioBlock",
    "IndicatorDecisionBlock",  # NEW: Indicator-based (replaces LLM)
    "LLMDecisionBlock",  # Kept for backwards compatibility
    "RiskBlock",
    "ExecutionBlock",
    "TradingOrchestrator",
]
