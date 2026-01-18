"""Risk management service for validating trading decisions."""

from decimal import Decimal
from typing import Optional

from ..core.config import config
from ..core.logger import get_logger
from ..models.bot import Bot
from ..models.position import Position, PositionStatus

logger = get_logger(__name__)


def _to_decimal(value) -> Decimal:
    """Convert any numeric value to Decimal."""
    return Decimal(str(value))


class RiskManagerService:
    """Service for validating trading decisions against risk parameters."""

    @staticmethod
    def validate_entry(
        bot: Bot, decision: dict, current_positions: list[Position], current_price: Decimal
    ) -> tuple[bool, str]:
        """Validate a new position entry against risk parameters."""
        try:
            size_pct = _to_decimal(decision.get("size_pct", config.DEFAULT_POSITION_SIZE_PCT))
            symbol = decision.get("symbol", "")
            leverage = _to_decimal(config.DEFAULT_LEVERAGE)

            # Check position size constraint (25% max)
            max_position_pct = _to_decimal(bot.risk_params.get("max_position_pct", 0.25))
            if size_pct > max_position_pct:
                return False, f"Position size {size_pct:.1%} exceeds max {max_position_pct:.1%}"

            # Check total margin exposure (95% max)
            open_positions = [p for p in current_positions if p.status == PositionStatus.OPEN]
            current_margin = sum(p.entry_price * p.quantity / p.leverage for p in open_positions)
            new_margin = bot.capital * size_pct
            new_total_margin = current_margin + new_margin
            max_exposure = bot.capital * Decimal("0.95")

            if new_total_margin > max_exposure:
                return False, f"Total margin ${new_total_margin:,.2f} would exceed max ${max_exposure:,.2f}"

            # Check for existing position in symbol
            if any(p.symbol == symbol for p in open_positions):
                return False, f"Already have open position in {symbol}"

            # Extract and validate prices
            stop_loss_price = decision.get("stop_loss")
            take_profit_price = decision.get("take_profit")
            entry_price = decision.get("entry_price") or decision.get("price") or float(current_price)

            if not stop_loss_price or stop_loss_price <= 0:
                return False, f"Invalid stop loss price: {stop_loss_price}"
            if not take_profit_price or take_profit_price <= 0:
                return False, f"Invalid take profit price: {take_profit_price}"

            entry_price = _to_decimal(entry_price)
            stop_loss_price = _to_decimal(stop_loss_price)
            take_profit_price = _to_decimal(take_profit_price)

            # Determine side (default to long)
            side = decision.get("side", "long").lower()
            if side not in ["long", "short"]:
                side = "long"

            # Validate price relationships and calculate percentages
            if side == "long":
                if not (stop_loss_price < entry_price < take_profit_price):
                    return False, f"Invalid LONG prices: SL({stop_loss_price:,.2f}) < ENTRY({entry_price:,.2f}) < TP({take_profit_price:,.2f})"
                stop_loss_pct = (entry_price - stop_loss_price) / entry_price
                take_profit_pct = (take_profit_price - entry_price) / entry_price
            else:
                if not (take_profit_price < entry_price < stop_loss_price):
                    return False, f"Invalid SHORT prices: TP({take_profit_price:,.2f}) < ENTRY({entry_price:,.2f}) < SL({stop_loss_price:,.2f})"
                stop_loss_pct = (stop_loss_price - entry_price) / entry_price
                take_profit_pct = (entry_price - take_profit_price) / entry_price

            # Minimum stop-loss distance (1.5% to avoid noise)
            min_sl_distance = Decimal("0.015")
            if stop_loss_pct < min_sl_distance:
                return False, f"Stop-loss distance {stop_loss_pct:.2%} below minimum {min_sl_distance:.1%}"

            # Risk/reward ratio (minimum 2:1)
            risk_reward = take_profit_pct / stop_loss_pct if stop_loss_pct > 0 else 0
            if risk_reward < 2.0:
                return False, f"Risk/reward ratio {risk_reward:.2f} below 2.0"

            # Fee protection - ensure trade is profitable after 0.10% round-trip fees
            fee_pct = Decimal("0.0010")
            position_notional = new_margin * leverage
            expected_profit = position_notional * take_profit_pct
            total_fees = position_notional * fee_pct
            net_profit = expected_profit - total_fees
            min_net_profit = Decimal("5.0")

            if net_profit < min_net_profit:
                return False, f"Net profit ${net_profit:.2f} below minimum ${min_net_profit:.2f}"

            # Minimum position size ($100)
            if new_margin < Decimal("100"):
                return False, f"Position size ${new_margin:,.2f} below minimum $100"

            logger.info(
                f"Entry validated: {symbol} {side.upper()} | "
                f"Entry: ${entry_price:,.2f} SL: {stop_loss_pct:.2%} TP: {take_profit_pct:.2%} R:R={risk_reward:.1f}"
            )
            return True, "Validation passed"

        except Exception as e:
            logger.error(f"Error validating entry: {e}")
            return False, f"Validation error: {str(e)}"

    @staticmethod
    def check_drawdown(bot: Bot, current_portfolio_value: Decimal) -> tuple[bool, Optional[str]]:
        """Check if current drawdown is within acceptable limits."""
        try:
            drawdown = (bot.capital - current_portfolio_value) / bot.capital
            max_drawdown_pct = _to_decimal(bot.risk_params.get("max_drawdown_pct", 0.20))

            if drawdown >= max_drawdown_pct:
                return False, f"Drawdown {drawdown:.1%} exceeds max {max_drawdown_pct:.1%}"

            if drawdown >= max_drawdown_pct * Decimal("0.80"):
                return True, f"Approaching max drawdown: {drawdown:.1%} (max: {max_drawdown_pct:.1%})"

            return True, None

        except Exception as e:
            logger.error(f"Error checking drawdown: {e}")
            return False, f"Drawdown check error: {str(e)}"

    @staticmethod
    def check_trade_frequency(bot: Bot, trades_today: int) -> tuple[bool, str]:
        """Check if trading frequency is within limits."""
        try:
            max_trades = bot.risk_params.get("max_trades_per_day", 10)

            if trades_today >= max_trades:
                return False, f"Daily trade limit reached: {trades_today}/{max_trades}"

            if trades_today >= int(max_trades * 0.80):
                return True, f"Approaching daily limit: {trades_today}/{max_trades}"

            return True, "Within daily trade limit"

        except Exception as e:
            logger.error(f"Error checking trade frequency: {e}")
            return False, f"Frequency check error: {str(e)}"

    @staticmethod
    def validate_leverage(leverage: float, max_leverage: float = 10.0) -> tuple[bool, str]:
        """Validate leverage is within acceptable limits."""
        if leverage <= 0:
            return False, "Leverage must be positive"
        if leverage > max_leverage:
            return False, f"Leverage {leverage}x exceeds max {max_leverage}x"
        return True, "Leverage within limits"

    @staticmethod
    def calculate_position_size(
        capital: Decimal,
        size_pct: Decimal,
        current_price: Decimal,
        confidence: Optional[Decimal] = None,
        leverage: Decimal = Decimal("1.0"),
    ) -> Decimal:
        """Calculate position size with optional confidence-based adjustment (Kelly-like)."""
        capital = _to_decimal(capital)
        size_pct = _to_decimal(size_pct)
        current_price = _to_decimal(current_price)
        leverage = _to_decimal(leverage)

        if capital <= 0:
            logger.warning(f"Cannot open position with capital: ${capital:,.2f}")
            return Decimal("0")

        position_value = capital * size_pct * leverage

        # Adjust position size based on confidence (0.3-0.9 maps to 50%-120% of base)
        if confidence is not None:
            confidence = _to_decimal(confidence)
            min_adj, max_adj = Decimal("0.5"), Decimal("1.2")

            if confidence < Decimal("0.3"):
                adjustment = min_adj
            elif confidence > Decimal("0.9"):
                adjustment = max_adj
            else:
                normalized = (confidence - Decimal("0.3")) / Decimal("0.6")
                adjustment = min_adj + (max_adj - min_adj) * normalized

            position_value *= adjustment

        return position_value / current_price

    @staticmethod
    def calculate_stop_loss_price(entry_price: Decimal, stop_loss_pct: Decimal, side: str) -> Decimal:
        """Calculate stop loss price based on position side."""
        multiplier = Decimal("1") - stop_loss_pct if side.lower() == "long" else Decimal("1") + stop_loss_pct
        return entry_price * multiplier

    @staticmethod
    def calculate_take_profit_price(entry_price: Decimal, take_profit_pct: Decimal, side: str) -> Decimal:
        """Calculate take profit price based on position side."""
        multiplier = Decimal("1") + take_profit_pct if side.lower() == "long" else Decimal("1") - take_profit_pct
        return entry_price * multiplier

    @staticmethod
    def validate_complete_decision(
        bot: Bot,
        decision: dict,
        current_positions: list[Position],
        current_price: Decimal,
        trades_today: int,
        portfolio_value: Optional[Decimal] = None,
    ) -> tuple[bool, str]:
        """Perform complete validation of a trading decision."""
        if decision.get("action", "") != "entry":
            return True, f"No validation needed for {decision.get('action', '')}"

        # Sequential validation checks
        freq_valid, freq_msg = RiskManagerService.check_trade_frequency(bot, trades_today)
        if not freq_valid:
            return False, freq_msg

        dd_valid, dd_msg = RiskManagerService.check_drawdown(bot, portfolio_value or bot.capital)
        if not dd_valid:
            return False, dd_msg

        entry_valid, entry_msg = RiskManagerService.validate_entry(
            bot, decision, current_positions, current_price
        )
        if not entry_valid:
            return False, entry_msg

        return True, "All validations passed"
