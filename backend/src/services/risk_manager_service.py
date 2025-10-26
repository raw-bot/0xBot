"""Risk management service for validating trading decisions."""

import uuid
from decimal import Decimal
from typing import Optional

from ..models.bot import Bot
from ..models.position import Position, PositionStatus
from ..core.logger import get_logger

logger = get_logger(__name__)


class RiskManagerService:
    """Service for validating trading decisions against risk parameters."""
    
    @staticmethod
    def validate_entry(
        bot: Bot,
        decision: dict,
        current_positions: list[Position],
        current_price: Decimal
    ) -> tuple[bool, str]:
        """
        Validate a new position entry against risk parameters.
        
        Args:
            bot: Bot instance with risk parameters
            decision: LLM decision dict with entry details
            current_positions: List of current open positions
            current_price: Current market price
            
        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            # Extract decision details
            size_pct = Decimal(str(decision.get('size_pct', 0)))
            symbol = decision.get('symbol', '')
            
            # 1. Check position size constraint
            max_position_pct = Decimal(str(bot.risk_params.get('max_position_pct', 0.15)))  # 15% max au lieu de 10%
            if size_pct > max_position_pct:
                return False, f"Position size {size_pct:.1%} exceeds max {max_position_pct:.1%}"
            
            # 2. Check total exposure
            total_exposure = sum(pos.position_value for pos in current_positions if pos.status == PositionStatus.OPEN)
            position_value = bot.capital * size_pct
            new_total_exposure = total_exposure + position_value
            
            # Max total exposure: 85% of capital (permet plus d'utilisation du capital)
            max_exposure = bot.capital * Decimal("0.85")
            if new_total_exposure > max_exposure:
                return False, f"Total exposure ${new_total_exposure:,.2f} would exceed max ${max_exposure:,.2f}"
            
            # 3. Check if already have position in this symbol
            existing_position = any(pos.symbol == symbol and pos.status == PositionStatus.OPEN for pos in current_positions)
            if existing_position:
                return False, f"Already have open position in {symbol}"
            
            # 4. Validate stop loss and take profit
            stop_loss_pct = decision.get('stop_loss_pct', 0)
            take_profit_pct = decision.get('take_profit_pct', 0)
            
            if stop_loss_pct <= 0:
                return False, "Stop loss percentage must be positive"
            
            if take_profit_pct <= 0:
                return False, "Take profit percentage must be positive"
            
            # Risk/reward ratio should be reasonable (min 1:1.3)
            risk_reward = take_profit_pct / stop_loss_pct if stop_loss_pct > 0 else 0
            if risk_reward < 1.3:  # Légèrement plus permissif
                return False, f"Risk/reward ratio {risk_reward:.2f} too low (min 1.3)"
            
            # 5. Check minimum position size (at least $50 for meaningful trades)
            if position_value < Decimal("50"):
                return False, f"Position size ${position_value:,.2f} below minimum $50"
            
            logger.info(f"Entry validation passed for {symbol}")
            return True, "Validation passed"
            
        except Exception as e:
            logger.error(f"Error validating entry: {e}")
            return False, f"Validation error: {str(e)}"
    
    @staticmethod
    def check_drawdown(
        bot: Bot,
        current_portfolio_value: Decimal
    ) -> tuple[bool, Optional[str]]:
        """
        Check if current drawdown is within acceptable limits.
        
        Args:
            bot: Bot instance with risk parameters
            current_portfolio_value: Current total portfolio value
            
        Returns:
            Tuple of (is_within_limit, warning_message)
        """
        try:
            initial_capital = bot.capital
            drawdown = (initial_capital - current_portfolio_value) / initial_capital
            
            max_drawdown_pct = Decimal(str(bot.risk_params.get('max_drawdown_pct', 0.20)))
            
            if drawdown >= max_drawdown_pct:
                return False, f"Drawdown {drawdown:.1%} exceeds max {max_drawdown_pct:.1%}"
            
            # Warning at 80% of max drawdown
            warning_threshold = max_drawdown_pct * Decimal("0.80")
            if drawdown >= warning_threshold:
                return True, f"Approaching max drawdown: {drawdown:.1%} (max: {max_drawdown_pct:.1%})"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error checking drawdown: {e}")
            return False, f"Drawdown check error: {str(e)}"
    
    @staticmethod
    def check_trade_frequency(
        bot: Bot,
        trades_today: int
    ) -> tuple[bool, str]:
        """
        Check if trading frequency is within limits.
        
        Args:
            bot: Bot instance with risk parameters
            trades_today: Number of trades executed today
            
        Returns:
            Tuple of (is_within_limit, message)
        """
        try:
            max_trades = bot.risk_params.get('max_trades_per_day', 10)
            
            if trades_today >= max_trades:
                return False, f"Daily trade limit reached: {trades_today}/{max_trades}"
            
            # Warning at 80% of limit
            warning_threshold = int(max_trades * 0.80)
            if trades_today >= warning_threshold:
                return True, f"Approaching daily limit: {trades_today}/{max_trades}"
            
            return True, "Within daily trade limit"
            
        except Exception as e:
            logger.error(f"Error checking trade frequency: {e}")
            return False, f"Frequency check error: {str(e)}"
    
    @staticmethod
    def validate_leverage(
        leverage: float,
        max_leverage: float = 10.0
    ) -> tuple[bool, str]:
        """
        Validate leverage is within acceptable limits.
        
        Args:
            leverage: Requested leverage
            max_leverage: Maximum allowed leverage (default: 10x)
            
        Returns:
            Tuple of (is_valid, message)
        """
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
        leverage: float = 1.0
    ) -> Decimal:
        """
        Calculate position size in base currency.
        
        Args:
            capital: Available capital
            size_pct: Position size as percentage (0.10 = 10%)
            current_price: Current market price
            leverage: Leverage multiplier (default: 1.0 = no leverage)
            
        Returns:
            Position quantity in base currency
        """
        position_value = capital * size_pct * Decimal(str(leverage))
        quantity = position_value / current_price
        return quantity
    
    @staticmethod
    def calculate_stop_loss_price(
        entry_price: Decimal,
        stop_loss_pct: Decimal,
        side: str
    ) -> Decimal:
        """
        Calculate stop loss price.
        
        Args:
            entry_price: Entry price
            stop_loss_pct: Stop loss distance as percentage (0.05 = 5%)
            side: Position side ('long' or 'short')
            
        Returns:
            Stop loss price
        """
        if side.lower() == 'long':
            # For long: stop loss is below entry
            return entry_price * (Decimal("1") - stop_loss_pct)
        else:
            # For short: stop loss is above entry
            return entry_price * (Decimal("1") + stop_loss_pct)
    
    @staticmethod
    def calculate_take_profit_price(
        entry_price: Decimal,
        take_profit_pct: Decimal,
        side: str
    ) -> Decimal:
        """
        Calculate take profit price.
        
        Args:
            entry_price: Entry price
            take_profit_pct: Take profit distance as percentage (0.10 = 10%)
            side: Position side ('long' or 'short')
            
        Returns:
            Take profit price
        """
        if side.lower() == 'long':
            # For long: take profit is above entry
            return entry_price * (Decimal("1") + take_profit_pct)
        else:
            # For short: take profit is below entry
            return entry_price * (Decimal("1") - take_profit_pct)
    
    @staticmethod
    def validate_complete_decision(
        bot: Bot,
        decision: dict,
        current_positions: list[Position],
        current_price: Decimal,
        trades_today: int,
        portfolio_value: Optional[Decimal] = None
    ) -> tuple[bool, str]:
        """
        Perform complete validation of a trading decision.
        
        Args:
            bot: Bot instance
            decision: LLM decision
            current_positions: Current open positions
            current_price: Current market price
            trades_today: Number of trades today
            portfolio_value: Optional pre-calculated portfolio value (to avoid lazy loading)
            
        Returns:
            Tuple of (is_valid, message)
        """
        action = decision.get('action', '')
        
        # Only validate entry decisions
        if action != 'entry':
            return True, f"No validation needed for {action}"
        
        # Check trade frequency
        freq_valid, freq_msg = RiskManagerService.check_trade_frequency(bot, trades_today)
        if not freq_valid:
            return False, freq_msg
        
        # Check drawdown (use provided portfolio_value if available)
        if portfolio_value is None:
            portfolio_value = bot.capital  # Fallback to capital only
        dd_valid, dd_msg = RiskManagerService.check_drawdown(bot, portfolio_value)
        if not dd_valid:
            return False, dd_msg
        
        # Validate entry
        entry_valid, entry_msg = RiskManagerService.validate_entry(
            bot, decision, current_positions, current_price
        )
        if not entry_valid:
            return False, entry_msg
        
        logger.info("Complete decision validation passed")
        return True, "All validations passed"