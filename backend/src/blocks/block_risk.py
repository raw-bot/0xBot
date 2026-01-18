"""Block: Risk Validation - Validates trades against risk parameters."""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Tuple

from ..core.logger import get_logger
from ..models.position import Position, PositionSide, PositionStatus

logger = get_logger(__name__)

MIN_POSITION_VALUE = Decimal("50")


@dataclass
class ValidationResult:
    """Result of a risk validation check."""

    is_valid: bool
    reason: str

    def __bool__(self):
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
        size_pct = Decimal(str(size_pct))

        if size_pct > self.max_position_pct:
            return ValidationResult(
                False, f"Position size {size_pct:.1%} exceeds max {self.max_position_pct:.1%}"
            )

        if self._has_open_position(symbol, current_positions):
            return ValidationResult(False, f"Already have position in {symbol}")

        margin_check = self._check_margin_exposure(size_pct, capital, current_positions)
        if not margin_check:
            return margin_check

        sl_tp_check = self._validate_sl_tp_relationship(side, entry_price, stop_loss, take_profit)
        if not sl_tp_check:
            return sl_tp_check

        rr_check = self._check_risk_reward(side, entry_price, stop_loss, take_profit)
        if not rr_check:
            return rr_check

        position_value = capital * size_pct
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
            if current_price <= position.stop_loss:
                return True, "stop_loss"
            if current_price >= position.take_profit:
                return True, "take_profit"
        else:
            if current_price >= position.stop_loss:
                return True, "stop_loss"
            if current_price <= position.take_profit:
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
