"""
Block: Indicator-Based Decision - Replaces LLM with professional indicators.

This block uses tested technical indicators instead of LLM for trading decisions.
Advantages:
- Deterministic (same data = same signal)
- Fast (<10ms vs 15s for LLM)
- Backtestable
- Transparent (easy to understand why trade)
- Free (no API costs)
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logger import get_logger
from ..services.indicator_strategy_service import (
    IndicatorSignal,
    IndicatorStrategyService,
    SignalType,
)
from ..services.kelly_position_sizing_service import KellyPositionSizingService

logger = get_logger(__name__)


@dataclass
class TradingDecision:
    """A trading decision from indicator analysis."""

    symbol: str
    signal: str  # "buy"|"sell"|"close"|"hold"
    confidence: float
    side: str  # "long"|"short"
    entry_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    size_pct: float = 0.10
    leverage: int = 1
    reasoning: str = ""
    signal_type: str = ""


class IndicatorDecisionBlock:
    """Uses professional indicators for trading decisions (no LLM)."""

    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.strategy = IndicatorStrategyService()
        self.db_session = db_session
        self.kelly_sizing = KellyPositionSizingService(db_session) if db_session else None

    async def get_decisions(
        self,
        market_data: Dict[str, Any],
        portfolio_context: Dict[str, Any],
        bot_name: str = "0xBot",
    ) -> Dict[str, TradingDecision]:
        """
        Get trading decisions for all symbols using indicators.

        Args:
            market_data: Dict of symbol -> market snapshot
            portfolio_context: Current portfolio state
            bot_name: Bot identifier

        Returns:
            Dict of symbol -> TradingDecision
        """
        try:
            decisions = {}
            # Handle both Position objects and dicts
            raw_positions = portfolio_context.get("positions", [])
            positions = {}
            for p in raw_positions:
                if hasattr(p, "symbol"):
                    positions[p.symbol] = p  # Position object
                elif isinstance(p, dict):
                    positions[p["symbol"]] = p  # Dict format
            bot_id = portfolio_context.get("bot_id", "")

            for symbol, market_snapshot in market_data.items():
                logger.debug(f"Analyzing {symbol}...")

                # Convert MarketSnapshot dataclass to dict if needed
                snapshot_dict = (
                    asdict(market_snapshot)
                    if hasattr(market_snapshot, "__dataclass_fields__")
                    else market_snapshot
                )

                # Get indicator signal
                indicator_signal = self.strategy.generate_signal(
                    symbol=symbol,
                    market_snapshot=snapshot_dict,
                    current_position=positions.get(symbol),
                )

                # Validate signal
                is_valid, validation_reason = self.strategy.validate_signal(indicator_signal)

                if not is_valid:
                    logger.debug(f"{symbol}: Invalid signal - {validation_reason}")
                    continue

                # Convert indicator signal to trading decision
                decision = self._convert_to_decision(indicator_signal, symbol, portfolio_context)

                if decision:
                    decisions[symbol] = decision
                    logger.info(
                        f"{symbol}: {decision.signal} "
                        f"({decision.confidence*100:.0f}% confidence) - {decision.reasoning}"
                    )

            return decisions

        except Exception as e:
            logger.error(f"Error getting indicator decisions: {e}", exc_info=True)
            return {}

    def _convert_to_decision(
        self,
        indicator_signal: IndicatorSignal,
        symbol: str,
        portfolio_context: Dict[str, Any],
    ) -> Optional[TradingDecision]:
        """Convert indicator signal to trading decision."""

        # Determine signal type and side
        if indicator_signal.signal_type == SignalType.BUY_PULLBACK:
            signal = "buy_to_enter"
            side = "long"
        elif indicator_signal.signal_type == SignalType.BUY_BREAKOUT:
            signal = "buy_to_enter"
            side = "long"
        elif indicator_signal.signal_type == SignalType.CLOSE_LONG:
            signal = "close"
            side = "long"
        elif indicator_signal.signal_type == SignalType.CLOSE_SHORT:
            signal = "close"
            side = "short"
        elif indicator_signal.signal_type == SignalType.SELL_SHORT:
            signal = "sell_to_enter"
            side = "short"
        else:
            return None

        # Get position size
        size_pct = float(indicator_signal.size_pct)

        # Format stop loss and take profit as Decimal
        stop_loss = Decimal(str(indicator_signal.stop_loss)) if indicator_signal.stop_loss else None
        take_profit = Decimal(str(indicator_signal.take_profit)) if indicator_signal.take_profit else None

        return TradingDecision(
            symbol=symbol,
            signal=signal,
            confidence=float(indicator_signal.confidence),
            side=side,
            entry_price=indicator_signal.entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            size_pct=size_pct,
            leverage=indicator_signal.leverage,
            reasoning=indicator_signal.reasoning,
            signal_type=indicator_signal.signal_type.value,
        )

    def format_decisions_for_api(self, decisions: Dict[str, TradingDecision]) -> Dict[str, dict[str, Any]]:
        """Format decisions for API response."""
        return {
            symbol: {
                "signal": decision.signal,
                "confidence": decision.confidence,
                "side": decision.side,
                "entry_price": float(decision.entry_price) if decision.entry_price else None,
                "stop_loss": decision.stop_loss,
                "take_profit": decision.take_profit,
                "size_pct": decision.size_pct,
                "leverage": decision.leverage,
                "reasoning": decision.reasoning,
                "signal_type": decision.signal_type,
                "timestamp": datetime.utcnow().isoformat(),
            }
            for symbol, decision in decisions.items()
        }
