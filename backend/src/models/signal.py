"""Signal types and decision models for trading."""

from enum import Enum
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


class SignalType(Enum):
    """Unified signal types for all decision blocks."""

    # Entry signals
    BUY_TO_ENTER = "buy_to_enter"
    SELL_TO_ENTER = "sell_to_enter"

    # Exit signals
    CLOSE = "close"

    # Neutral
    HOLD = "hold"

    def __str__(self) -> str:
        """Return the string value of the signal."""
        return self.value


class SignalSide(Enum):
    """Position side."""

    LONG = "long"
    SHORT = "short"

    def __str__(self) -> str:
        return self.value


@dataclass
class TradingSignal:
    """Unified trading signal from any decision block."""

    symbol: str
    signal_type: SignalType  # Use enum, not string
    side: Optional[SignalSide] = None  # Only for entry signals
    confidence: float = 0.5  # 0-1
    reasoning: str = ""
    entry_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    size_pct: float = 0.0
    leverage: int = 1

    @property
    def is_entry_signal(self) -> bool:
        """Check if this is an entry signal."""
        return self.signal_type in [SignalType.BUY_TO_ENTER, SignalType.SELL_TO_ENTER]

    @property
    def is_exit_signal(self) -> bool:
        """Check if this is an exit signal."""
        return self.signal_type == SignalType.CLOSE

    @property
    def is_hold_signal(self) -> bool:
        """Check if this is a hold signal."""
        return self.signal_type == SignalType.HOLD
