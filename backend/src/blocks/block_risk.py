"""Block: Risk Validation - Validates trades against risk parameters."""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Tuple, Dict, Any, Optional

from ..core.logger import get_logger
from ..models.position import Position, PositionSide, PositionStatus

logger = get_logger(__name__)

MIN_POSITION_VALUE = Decimal("50")
PYRAMID_MAX_POSITIONS = 2
PYRAMID_FIRST_ENTRY_PCT = 0.10
PYRAMID_SECOND_ENTRY_PCT = 0.05
PYRAMID_MAX_TOTAL_PCT = 0.15


@dataclass
class ValidationResult:
    """Result of a risk validation check."""

    is_valid: bool
    reason: str

    def __bool__(self) -> bool:
        return self.is_valid


class RiskBlock:
    """Validates trading decisions against risk parameters."""

    def __init__(
        self,
        max_position_pct: float = 0.25,
        max_exposure_pct: float = 0.95,
        min_risk_reward: float = 1.3,
    ):
        self.max_position_pct = Decimal(str(max_position_pct))
        self.max_exposure_pct = Decimal(str(max_exposure_pct))
        self.min_risk_reward = min_risk_reward

    def validate_entry(
        self,
        symbol: str,
        side: str,
        size_pct: float,
        entry_price: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal,
        capital: Decimal,
        current_positions: List[Position],
    ) -> ValidationResult:
        """Validate a new position entry."""
        size_pct_decimal = Decimal(str(size_pct))

        if size_pct_decimal > self.max_position_pct:
            return ValidationResult(
                False, f"Position size {size_pct:.1%} exceeds max {self.max_position_pct:.1%}"
            )

        if self._has_open_position(symbol, current_positions):
            return ValidationResult(False, f"Already have position in {symbol}")

        margin_check = self._check_margin_exposure(size_pct_decimal, capital, current_positions)
        if not margin_check:
            return margin_check

        sl_tp_check = self._validate_sl_tp_relationship(side, entry_price, stop_loss, take_profit)
        if not sl_tp_check:
            return sl_tp_check

        rr_check = self._check_risk_reward(side, entry_price, stop_loss, take_profit)
        if not rr_check:
            return rr_check

        position_value = capital * size_pct_decimal
        if position_value < MIN_POSITION_VALUE:
            return ValidationResult(False, f"Position ${position_value:,.2f} below minimum $50")

        return ValidationResult(True, "Validation passed")

    def check_exit_conditions(
        self,
        position: Position,
        current_price: Decimal,
    ) -> Tuple[bool, str]:
        """Check if position should be closed."""
        if position.side == PositionSide.LONG:
            if position.stop_loss is not None and current_price <= position.stop_loss:
                return True, "stop_loss"
            if position.take_profit is not None and current_price >= position.take_profit:
                return True, "take_profit"
        else:
            if position.stop_loss is not None and current_price >= position.stop_loss:
                return True, "stop_loss"
            if position.take_profit is not None and current_price <= position.take_profit:
                return True, "take_profit"

        return False, ""

    def _has_open_position(self, symbol: str, positions: List[Position]) -> bool:
        """Check if there's an open position for the symbol."""
        return any(p.symbol == symbol and p.status == PositionStatus.OPEN for p in positions)

    def _check_margin_exposure(
        self,
        size_pct: Decimal,
        capital: Decimal,
        positions: List[Position],
    ) -> ValidationResult:
        """Check if new position would exceed margin limits."""
        current_margin = sum(
            (p.entry_price * p.quantity / p.leverage)
            for p in positions
            if p.status == PositionStatus.OPEN
        )
        new_margin = capital * size_pct
        total_margin = current_margin + new_margin
        max_margin = capital * self.max_exposure_pct

        if total_margin > max_margin:
            return ValidationResult(
                False, f"Margin ${total_margin:,.2f} exceeds max ${max_margin:,.2f}"
            )
        return ValidationResult(True, "")

    def _validate_sl_tp_relationship(
        self,
        side: str,
        entry_price: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal,
    ) -> ValidationResult:
        """Validate SL/TP are on correct sides of entry."""
        if side == "long":
            if not (stop_loss < entry_price < take_profit):
                return ValidationResult(
                    False,
                    f"Invalid LONG: SL({stop_loss:,.2f}) < Entry({entry_price:,.2f}) < TP({take_profit:,.2f})",
                )
        else:
            if not (take_profit < entry_price < stop_loss):
                return ValidationResult(
                    False,
                    f"Invalid SHORT: TP({take_profit:,.2f}) < Entry({entry_price:,.2f}) < SL({stop_loss:,.2f})",
                )
        return ValidationResult(True, "")

    def _check_risk_reward(
        self,
        side: str,
        entry_price: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal,
    ) -> ValidationResult:
        """Check if risk/reward ratio meets minimum threshold."""
        if side == "long":
            sl_pct = (entry_price - stop_loss) / entry_price
            tp_pct = (take_profit - entry_price) / entry_price
        else:
            sl_pct = (stop_loss - entry_price) / entry_price
            tp_pct = (entry_price - take_profit) / entry_price

        if sl_pct > 0:
            risk_reward = tp_pct / sl_pct
            if risk_reward < self.min_risk_reward:
                return ValidationResult(
                    False, f"R/R ratio {risk_reward:.2f} < min {self.min_risk_reward}"
                )
        return ValidationResult(True, "")

    def calculate_microstructure_stops(
        self,
        entry_price: Decimal,
        side: str,
        atr: Optional[Decimal] = None,
        kumo_width: Optional[Decimal] = None,
        volatility_level: str = "medium",
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate microstructure-aware stop loss and take profit.

        Args:
            entry_price: Entry price for the position
            side: "long" or "short"
            atr: Average True Range for volatility
            kumo_width: Ichimoku cloud width (for tight stops)
            volatility_level: "low", "medium", "high" for adaptive sizing

        Returns:
            Tuple of (stop_loss, take_profit)
        """
        atr = atr or Decimal("0.02") * entry_price  # 2% default

        # Calculate SL distance based on volatility and cloud width
        volatility_multiplier = Decimal(str({"low": 1.5, "medium": 2.0, "high": 3.0}.get(
            volatility_level, 2.0
        )))

        # Tighter stops when cloud is tight (0.5% of price)
        # Wider stops when volatility high (3x ATR)
        sl_distance = min(volatility_multiplier * atr, Decimal("0.005") * entry_price)

        # If cloud width is tight, use tighter stops
        if kumo_width and kumo_width < Decimal("0.01") * entry_price:
            sl_distance = Decimal("0.015") * entry_price  # 1.5% tighter

        if side == "long":
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + (sl_distance * Decimal("2"))  # 2x for R/R
        else:  # short
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - (sl_distance * Decimal("2"))

        logger.info(
            f"[MICROSTRUCTURE_STOPS] Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}, "
            f"ATR: {atr}, Volatility: {volatility_level}"
        )

        return stop_loss, take_profit

    def detect_structure_breaks(
        self,
        position: Position,
        current_price: Decimal,
        signals: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Detect if position should exit due to key market structure breaks.

        Args:
            position: Current open position
            current_price: Current market price
            signals: Dictionary of indicator signals

        Returns:
            Tuple of (should_close, reason)
        """
        signals = signals or {}

        # Break Ichimoku cloud level = immediate exit
        if signals.get("price_breaks_kumo", False):
            return True, "ichimoku_cloud_break"

        # MACD changes direction = tighten stops
        if signals.get("macd_direction_change", False):
            return False, "tighten_stops"

        # Order flow reverses = close 50% position
        if signals.get("order_flow_reverses", False):
            return False, "close_half"

        # Price touches pre-set technical level
        if signals.get("breaks_key_level", False):
            return True, "key_level_break"

        return False, None

    def can_pyramid_entry(
        self,
        symbol: str,
        current_positions: List[Position],
        first_position_profitable: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if pyramid entry is allowed for this symbol.

        Requirements:
        - First entry: 6/6 signals (10%)
        - Second entry: 4/6 signals + first still profitable (5%)
        - Max: 2 positions per pair, never more than 15% total

        Args:
            symbol: Trading symbol
            current_positions: List of open positions
            first_position_profitable: Whether first position is still in profit

        Returns:
            Tuple of (can_pyramid, reason)
        """
        # Count positions for this symbol
        same_symbol_positions = [
            p for p in current_positions
            if p.symbol == symbol and p.status == PositionStatus.OPEN
        ]

        if len(same_symbol_positions) >= PYRAMID_MAX_POSITIONS:
            return False, f"Already at max {PYRAMID_MAX_POSITIONS} positions for {symbol}"

        if len(same_symbol_positions) == 1:
            if not first_position_profitable:
                return False, "First position not profitable - cannot pyramid"
            return True, "Second entry allowed"

        if len(same_symbol_positions) == 0:
            return True, "First entry allowed"

        return False, "Unknown pyramid state"

    def calculate_pyramid_size(
        self,
        entry_number: int,
        capital: Decimal,
        current_exposure: Decimal,
    ) -> Decimal:
        """
        Calculate position size for pyramid entries.

        - First entry: 10% of capital
        - Second entry: 5% of capital
        - Never exceed 15% total

        Args:
            entry_number: Which entry this is (1 or 2)
            capital: Total account capital
            current_exposure: Current total exposure

        Returns:
            Position size as percentage (0-1)
        """
        if entry_number == 1:
            size_pct = PYRAMID_FIRST_ENTRY_PCT
        elif entry_number == 2:
            size_pct = PYRAMID_SECOND_ENTRY_PCT
        else:
            return Decimal("0")

        size = capital * Decimal(str(size_pct))
        total_would_be = current_exposure + size
        max_total = capital * Decimal(str(PYRAMID_MAX_TOTAL_PCT))

        if total_would_be > max_total:
            logger.warning(
                f"[PYRAMID] Entry {entry_number} would exceed max 15% total. "
                f"Current: {current_exposure/capital:.1%}, Max: {max_total/capital:.1%}"
            )
            return Decimal("0")

        logger.info(
            f"[PYRAMID] Entry {entry_number}: {size_pct:.1%} = ${size:,.2f}, "
            f"Total exposure: {total_would_be/capital:.1%}"
        )

        return Decimal(str(size_pct))
