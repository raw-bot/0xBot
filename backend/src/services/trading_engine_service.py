"""Trading engine service - backward compatibility wrapper."""

from .trading_engine.service import TradingEngineService as TradingEngine

__all__ = ["TradingEngine"]
