"""Block: Risk Validation - Validates trades against risk parameters.

This block is responsible for:
- Validating position size limits
- Checking exposure limits
- Validating SL/TP relationships
- Risk/reward ratio checks
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Tuple

from ..core.config import config
from ..core.logger import get_logger
from ..models.position import Position, PositionStatus

logger = get_logger(__name__)


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
        """
        Validate a new position entry.

        Returns:
            ValidationResult with is_valid and reason
        """
        size_pct = Decimal(str(size_pct))

        # 1. Check position size
        if size_pct > self.max_position_pct:
            return ValidationResult(
                False, f"Position size {size_pct:.1%} exceeds max {self.max_position_pct:.1%}"
            )

        # 2. Check if already have position in symbol
        has_position = any(
            p.symbol == symbol and p.status == PositionStatus.OPEN for p in current_positions
        )
        if has_position:
            return ValidationResult(False, f"Already have position in {symbol}")

        # 3. Check margin exposure
        current_margin = sum(
            (p.entry_price * p.quantity / p.leverage)
            for p in current_positions
            if p.status == PositionStatus.OPEN
        )
        new_margin = capital * size_pct
        total_margin = current_margin + new_margin
        max_margin = capital * self.max_exposure_pct

        if total_margin > max_margin:
            return ValidationResult(
                False, f"Margin ${total_margin:,.2f} exceeds max ${max_margin:,.2f}"
            )

        # 4. Validate SL/TP relationships
        if side == "long":
            if not (stop_loss < entry_price < take_profit):
                return ValidationResult(
                    False,
                    f"Invalid LONG: SL({stop_loss:,.2f}) < Entry({entry_price:,.2f}) < TP({take_profit:,.2f})",
                )
            sl_pct = (entry_price - stop_loss) / entry_price
            tp_pct = (take_profit - entry_price) / entry_price
        else:
            if not (take_profit < entry_price < stop_loss):
                return ValidationResult(
                    False,
                    f"Invalid SHORT: TP({take_profit:,.2f}) < Entry({entry_price:,.2f}) < SL({stop_loss:,.2f})",
                )
            sl_pct = (stop_loss - entry_price) / entry_price
            tp_pct = (entry_price - take_profit) / entry_price

        # 5. Risk/reward ratio
        if sl_pct > 0:
            risk_reward = tp_pct / sl_pct
            if risk_reward < self.min_risk_reward:
                return ValidationResult(
                    False, f"R/R ratio {risk_reward:.2f} < min {self.min_risk_reward}"
                )

        # 6. Minimum position value
        position_value = capital * size_pct
        if position_value < Decimal("50"):
            return ValidationResult(False, f"Position ${position_value:,.2f} below minimum $50")

        logger.info(
            f"   💰 Entry: ${entry_price:,.2f} | "
            f"SL: ${stop_loss:,.2f} ({sl_pct:.1%}) | "
            f"TP: ${take_profit:,.2f} ({tp_pct:.1%}) | "
            f"Side: {side.upper()}"
        )
        logger.info(f"   ✅ Risk validation passed for {symbol}")

        return ValidationResult(True, "Validation passed")

    def check_exit_conditions(
        self,
        position: Position,
        current_price: Decimal,
    ) -> Tuple[bool, str]:
        """
        Check if position should be closed.

        Returns:
            Tuple of (should_exit, reason)
        """
        if position.side == "long":
            # Stop loss hit
            if current_price <= position.stop_loss:
                return True, "stop_loss"
            # Take profit hit
            if current_price >= position.take_profit:
                return True, "take_profit"
        else:  # short
            if current_price >= position.stop_loss:
                return True, "stop_loss"
            if current_price <= position.take_profit:
                return True, "take_profit"

        return False, ""
