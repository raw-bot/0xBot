"""Tests for risk manager service."""

import pytest
from decimal import Decimal
from uuid import uuid4

from src.services.risk_manager_service import RiskManagerService, _to_decimal
from src.models.bot import Bot
from src.models.position import Position, PositionStatus, PositionSide
from src.models.user import User


class TestToDecimal:
    """Tests for _to_decimal helper function."""

    def test_to_decimal_float(self):
        """Test converting float to Decimal."""
        result = _to_decimal(123.45)
        assert result == Decimal("123.45")

    def test_to_decimal_string(self):
        """Test converting string to Decimal."""
        result = _to_decimal("456.78")
        assert result == Decimal("456.78")

    def test_to_decimal_int(self):
        """Test converting int to Decimal."""
        result = _to_decimal(100)
        assert result == Decimal("100")

    def test_to_decimal_decimal(self):
        """Test Decimal input returns Decimal."""
        dec = Decimal("789.01")
        result = _to_decimal(dec)
        assert result == dec


class TestValidateEntry:
    """Tests for validate_entry method."""

    @pytest.fixture
    def bot_with_capital(self, test_bot):
        """Create a bot with sufficient capital."""
        test_bot.capital = Decimal("10000")
        test_bot.risk_params = {
            "max_position_pct": Decimal("0.25"),
            "max_drawdown_pct": Decimal("0.20"),
            "max_trades_per_day": 10,
        }
        return test_bot

    def test_validate_entry_long_valid(self, bot_with_capital):
        """Test valid long entry validation."""
        decision = {
            "symbol": "BTC/USDT",
            "side": "long",
            "size_pct": Decimal("0.10"),
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("44000"),  # 2.2% below
            "take_profit": Decimal("47000"),  # 4.4% above
        }
        current_positions = []
        current_price = Decimal("45000")

        valid, msg = RiskManagerService.validate_entry(bot_with_capital, decision, current_positions, current_price)

        assert valid is True
        assert "Validation passed" in msg

    def test_validate_entry_short_valid(self, bot_with_capital):
        """Test valid short entry validation."""
        decision = {
            "symbol": "ETH/USDT",
            "side": "short",
            "size_pct": Decimal("0.15"),
            "entry_price": Decimal("3000"),
            "stop_loss": Decimal("3100"),  # 3.3% above for short
            "take_profit": Decimal("2700"),  # 10% below (R:R = 10/3.3 = 3.0 > 2.0)
        }
        current_positions = []
        current_price = Decimal("3000")

        valid, msg = RiskManagerService.validate_entry(bot_with_capital, decision, current_positions, current_price)

        assert valid is True

    def test_validate_entry_position_size_exceeds_max(self, bot_with_capital):
        """Test position size exceeding max."""
        decision = {
            "symbol": "BTC/USDT",
            "size_pct": Decimal("0.30"),  # Exceeds 0.25 max
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("44000"),
            "take_profit": Decimal("47000"),
        }
        current_positions = []

        valid, msg = RiskManagerService.validate_entry(bot_with_capital, decision, current_positions, Decimal("45000"))

        assert valid is False
        assert "exceeds max" in msg

    def test_validate_entry_margin_exceeds_max(self, bot_with_capital):
        """Test total margin exceeding 95% max."""
        # Create existing open position with large margin
        existing_position = Position(
            id=uuid4(),
            bot_id=bot_with_capital.id,
            symbol="ETH/USDT",
            side=PositionSide.LONG,
            status=PositionStatus.OPEN,
            entry_price=Decimal("3000"),
            quantity=Decimal("3"),  # 3 ETH × $3000 = $9000 margin
            leverage=Decimal("1"),
        )

        decision = {
            "symbol": "BTC/USDT",
            "size_pct": Decimal("0.10"),  # $1000 margin - total would be $10,000 (100% of capital)
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("44000"),
            "take_profit": Decimal("47000"),
        }

        valid, msg = RiskManagerService.validate_entry(
            bot_with_capital, decision, [existing_position], Decimal("45000")
        )

        assert valid is False
        assert "exceed max" in msg

    def test_validate_entry_symbol_already_open(self, bot_with_capital):
        """Test entry when position already open in symbol."""
        existing_position = Position(
            id=uuid4(),
            bot_id=bot_with_capital.id,
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            status=PositionStatus.OPEN,
            entry_price=Decimal("44000"),
            quantity=Decimal("0.1"),
            leverage=Decimal("1"),
        )

        decision = {
            "symbol": "BTC/USDT",  # Same symbol
            "size_pct": Decimal("0.10"),
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("44000"),
            "take_profit": Decimal("47000"),
        }

        valid, msg = RiskManagerService.validate_entry(
            bot_with_capital, decision, [existing_position], Decimal("45000")
        )

        assert valid is False
        assert "Already have open position" in msg

    def test_validate_entry_invalid_stop_loss(self, bot_with_capital):
        """Test entry with invalid stop loss (zero)."""
        decision = {
            "symbol": "BTC/USDT",
            "size_pct": Decimal("0.10"),
            "entry_price": Decimal("45000"),
            "stop_loss": 0,  # Invalid
            "take_profit": Decimal("47000"),
        }

        valid, msg = RiskManagerService.validate_entry(bot_with_capital, decision, [], Decimal("45000"))

        assert valid is False
        assert "Invalid stop loss" in msg

    def test_validate_entry_invalid_take_profit(self, bot_with_capital):
        """Test entry with invalid take profit (negative)."""
        decision = {
            "symbol": "BTC/USDT",
            "size_pct": Decimal("0.10"),
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("44000"),
            "take_profit": Decimal("-1000"),  # Invalid
        }

        valid, msg = RiskManagerService.validate_entry(bot_with_capital, decision, [], Decimal("45000"))

        assert valid is False
        assert "Invalid take profit" in msg

    def test_validate_entry_long_invalid_prices(self, bot_with_capital):
        """Test long entry with invalid price relationship."""
        decision = {
            "symbol": "BTC/USDT",
            "side": "long",
            "size_pct": Decimal("0.10"),
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("45000"),  # Must be less than entry for long
            "take_profit": Decimal("44000"),  # Must be greater than entry for long
        }

        valid, msg = RiskManagerService.validate_entry(bot_with_capital, decision, [], Decimal("45000"))

        assert valid is False
        assert "Invalid LONG prices" in msg

    def test_validate_entry_short_invalid_prices(self, bot_with_capital):
        """Test short entry with invalid price relationship."""
        decision = {
            "symbol": "BTC/USDT",
            "side": "short",
            "size_pct": Decimal("0.10"),
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("44000"),  # Must be greater than entry for short
            "take_profit": Decimal("46000"),  # Must be less than entry for short
        }

        valid, msg = RiskManagerService.validate_entry(bot_with_capital, decision, [], Decimal("45000"))

        assert valid is False
        assert "Invalid SHORT prices" in msg

    def test_validate_entry_stop_loss_too_close(self, bot_with_capital):
        """Test entry with stop loss too close (< 1.5%)."""
        decision = {
            "symbol": "BTC/USDT",
            "side": "long",
            "size_pct": Decimal("0.10"),
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("44400"),  # Only 1.3% below
            "take_profit": Decimal("47000"),
        }

        valid, msg = RiskManagerService.validate_entry(bot_with_capital, decision, [], Decimal("45000"))

        assert valid is False
        assert "below minimum" in msg

    def test_validate_entry_risk_reward_below_minimum(self, bot_with_capital):
        """Test entry with risk/reward < 2.0."""
        decision = {
            "symbol": "BTC/USDT",
            "side": "long",
            "size_pct": Decimal("0.10"),
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("44100"),  # 2.4% below
            "take_profit": Decimal("45100"),  # Only 0.2% above (R:R = 0.08)
        }

        valid, msg = RiskManagerService.validate_entry(bot_with_capital, decision, [], Decimal("45000"))

        assert valid is False
        assert "Risk/reward ratio" in msg

    def test_validate_entry_net_profit_below_minimum(self, bot_with_capital):
        """Test entry where net profit below $5 minimum."""
        decision = {
            "symbol": "BTC/USDT",
            "side": "long",
            "size_pct": Decimal("0.001"),  # Very small position ($10)
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("44100"),  # 2.4% below
            "take_profit": Decimal("48000"),  # 6.7% above
        }

        valid, msg = RiskManagerService.validate_entry(bot_with_capital, decision, [], Decimal("45000"))

        assert valid is False
        assert "Net profit" in msg or "below minimum" in msg

    def test_validate_entry_position_size_below_minimum(self, bot_with_capital):
        """Test entry with position size below $100."""
        decision = {
            "symbol": "BTC/USDT",
            "side": "long",
            "size_pct": Decimal("0.005"),  # $50 position
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("44100"),
            "take_profit": Decimal("48000"),
        }

        valid, msg = RiskManagerService.validate_entry(bot_with_capital, decision, [], Decimal("45000"))

        assert valid is False
        assert "below minimum $100" in msg

    def test_validate_entry_uses_current_price(self, bot_with_capital):
        """Test entry uses current price when entry_price not provided."""
        decision = {
            "symbol": "BTC/USDT",
            "size_pct": Decimal("0.10"),
            # No entry_price provided
            "stop_loss": Decimal("44000"),
            "take_profit": Decimal("47000"),
        }
        current_price = Decimal("45000")

        valid, msg = RiskManagerService.validate_entry(bot_with_capital, decision, [], current_price)

        assert valid is True

    def test_validate_entry_default_side_long(self, bot_with_capital):
        """Test entry defaults to long when side not provided."""
        decision = {
            "symbol": "BTC/USDT",
            "size_pct": Decimal("0.10"),
            "entry_price": Decimal("45000"),
            # No side provided
            "stop_loss": Decimal("44000"),
            "take_profit": Decimal("47000"),
        }

        valid, msg = RiskManagerService.validate_entry(bot_with_capital, decision, [], Decimal("45000"))

        assert valid is True


class TestCheckDrawdown:
    """Tests for check_drawdown method."""

    def test_check_drawdown_within_limits(self, test_bot):
        """Test drawdown within acceptable limits."""
        test_bot.capital = Decimal("10000")
        test_bot.risk_params = {"max_drawdown_pct": Decimal("0.20")}

        portfolio_value = Decimal("9500")  # 5% drawdown
        valid, msg = RiskManagerService.check_drawdown(test_bot, portfolio_value)

        assert valid is True
        assert msg is None

    def test_check_drawdown_approaching_limit(self, test_bot):
        """Test drawdown approaching limit (80% of max)."""
        test_bot.capital = Decimal("10000")
        test_bot.risk_params = {"max_drawdown_pct": Decimal("0.20")}

        portfolio_value = Decimal("8400")  # 16% drawdown (80% of 20%)
        valid, msg = RiskManagerService.check_drawdown(test_bot, portfolio_value)

        assert valid is True
        assert "Approaching" in msg

    def test_check_drawdown_exceeds_limit(self, test_bot):
        """Test drawdown exceeding limit."""
        test_bot.capital = Decimal("10000")
        test_bot.risk_params = {"max_drawdown_pct": Decimal("0.20")}

        portfolio_value = Decimal("7900")  # 21% drawdown
        valid, msg = RiskManagerService.check_drawdown(test_bot, portfolio_value)

        assert valid is False
        assert "exceeds max" in msg

    def test_check_drawdown_zero_portfolio_value(self, test_bot):
        """Test drawdown with zero portfolio value."""
        test_bot.capital = Decimal("10000")
        test_bot.risk_params = {"max_drawdown_pct": Decimal("0.20")}

        portfolio_value = Decimal("0")  # 100% drawdown
        valid, msg = RiskManagerService.check_drawdown(test_bot, portfolio_value)

        assert valid is False

    def test_check_drawdown_profitable_position(self, test_bot):
        """Test drawdown with profitable portfolio."""
        test_bot.capital = Decimal("10000")
        test_bot.risk_params = {"max_drawdown_pct": Decimal("0.20")}

        portfolio_value = Decimal("12000")  # Profit, not drawdown
        valid, msg = RiskManagerService.check_drawdown(test_bot, portfolio_value)

        assert valid is True


class TestCheckTradeFrequency:
    """Tests for check_trade_frequency method."""

    def test_check_trade_frequency_within_limit(self, test_bot):
        """Test trade frequency within limit."""
        test_bot.risk_params = {"max_trades_per_day": 10}

        valid, msg = RiskManagerService.check_trade_frequency(test_bot, 5)

        assert valid is True
        assert "Within daily trade limit" in msg

    def test_check_trade_frequency_approaching_limit(self, test_bot):
        """Test trade frequency approaching limit (80%)."""
        test_bot.risk_params = {"max_trades_per_day": 10}

        valid, msg = RiskManagerService.check_trade_frequency(test_bot, 8)

        assert valid is True
        assert "Approaching daily limit" in msg

    def test_check_trade_frequency_at_limit(self, test_bot):
        """Test trade frequency at limit."""
        test_bot.risk_params = {"max_trades_per_day": 10}

        valid, msg = RiskManagerService.check_trade_frequency(test_bot, 10)

        assert valid is False
        assert "limit reached" in msg

    def test_check_trade_frequency_exceeds_limit(self, test_bot):
        """Test trade frequency exceeding limit."""
        test_bot.risk_params = {"max_trades_per_day": 10}

        valid, msg = RiskManagerService.check_trade_frequency(test_bot, 12)

        assert valid is False


class TestValidateLeverage:
    """Tests for validate_leverage method."""

    def test_validate_leverage_valid(self):
        """Test valid leverage."""
        valid, msg = RiskManagerService.validate_leverage(5.0, 10.0)

        assert valid is True
        assert "within limits" in msg

    def test_validate_leverage_one(self):
        """Test 1x leverage (spot trading)."""
        valid, msg = RiskManagerService.validate_leverage(1.0)

        assert valid is True

    def test_validate_leverage_max(self):
        """Test leverage at max limit."""
        valid, msg = RiskManagerService.validate_leverage(10.0, 10.0)

        assert valid is True

    def test_validate_leverage_exceeds_max(self):
        """Test leverage exceeding max."""
        valid, msg = RiskManagerService.validate_leverage(15.0, 10.0)

        assert valid is False
        assert "exceeds max" in msg

    def test_validate_leverage_zero(self):
        """Test zero leverage (invalid)."""
        valid, msg = RiskManagerService.validate_leverage(0.0)

        assert valid is False
        assert "positive" in msg

    def test_validate_leverage_negative(self):
        """Test negative leverage (invalid)."""
        valid, msg = RiskManagerService.validate_leverage(-5.0)

        assert valid is False


class TestCalculatePositionSize:
    """Tests for calculate_position_size method."""

    def test_calculate_position_size_basic(self):
        """Test basic position size calculation."""
        capital = Decimal("10000")
        size_pct = Decimal("0.10")
        price = Decimal("50000")

        size = RiskManagerService.calculate_position_size(capital, size_pct, price)

        # (10000 × 0.10) / 50000 = 0.02 units
        assert size == Decimal("0.02")

    def test_calculate_position_size_with_leverage(self):
        """Test position size calculation with leverage."""
        capital = Decimal("10000")
        size_pct = Decimal("0.10")
        price = Decimal("50000")
        leverage = Decimal("2.0")

        size = RiskManagerService.calculate_position_size(capital, size_pct, price, leverage=leverage)

        # (10000 × 0.10 × 2) / 50000 = 0.04 units
        assert size == Decimal("0.04")

    def test_calculate_position_size_low_confidence(self):
        """Test position size with low confidence (0.3 = 50% of base)."""
        capital = Decimal("10000")
        size_pct = Decimal("0.10")
        price = Decimal("50000")
        confidence = Decimal("0.3")  # Minimum confidence

        size = RiskManagerService.calculate_position_size(capital, size_pct, price, confidence=confidence)

        # (10000 × 0.10 × 0.5) / 50000 = 0.01 units
        assert size == Decimal("0.01")

    def test_calculate_position_size_high_confidence(self):
        """Test position size with high confidence (0.9 = 120% of base)."""
        capital = Decimal("10000")
        size_pct = Decimal("0.10")
        price = Decimal("50000")
        confidence = Decimal("0.9")  # Maximum confidence

        size = RiskManagerService.calculate_position_size(capital, size_pct, price, confidence=confidence)

        # (10000 × 0.10 × 1.2) / 50000 = 0.024 units
        assert size == Decimal("0.024")

    def test_calculate_position_size_mid_confidence(self):
        """Test position size with mid confidence (0.6 = 85% of base)."""
        capital = Decimal("10000")
        size_pct = Decimal("0.10")
        price = Decimal("50000")
        confidence = Decimal("0.6")  # Mid-range

        size = RiskManagerService.calculate_position_size(capital, size_pct, price, confidence=confidence)

        # Should be between 0.01 and 0.024 (adjusted from 0.02)
        assert Decimal("0.01") < size < Decimal("0.024")

    def test_calculate_position_size_zero_capital(self):
        """Test position size with zero capital."""
        capital = Decimal("0")
        size_pct = Decimal("0.10")
        price = Decimal("50000")

        size = RiskManagerService.calculate_position_size(capital, size_pct, price)

        assert size == Decimal("0")

    def test_calculate_position_size_negative_capital(self):
        """Test position size with negative capital."""
        capital = Decimal("-1000")
        size_pct = Decimal("0.10")
        price = Decimal("50000")

        size = RiskManagerService.calculate_position_size(capital, size_pct, price)

        assert size == Decimal("0")


class TestCalculateStopLossPrice:
    """Tests for calculate_stop_loss_price method."""

    def test_calculate_stop_loss_long(self):
        """Test stop loss price for long position."""
        entry = Decimal("45000")
        sl_pct = Decimal("0.02")  # 2%

        sl_price = RiskManagerService.calculate_stop_loss_price(entry, sl_pct, "long")

        # 45000 × (1 - 0.02) = 44100
        assert sl_price == Decimal("44100")

    def test_calculate_stop_loss_short(self):
        """Test stop loss price for short position."""
        entry = Decimal("45000")
        sl_pct = Decimal("0.02")  # 2%

        sl_price = RiskManagerService.calculate_stop_loss_price(entry, sl_pct, "short")

        # 45000 × (1 + 0.02) = 45900
        assert sl_price == Decimal("45900")

    def test_calculate_stop_loss_case_insensitive(self):
        """Test stop loss calculation is case insensitive."""
        entry = Decimal("45000")
        sl_pct = Decimal("0.02")

        sl_price_long = RiskManagerService.calculate_stop_loss_price(entry, sl_pct, "LONG")
        sl_price_short = RiskManagerService.calculate_stop_loss_price(entry, sl_pct, "SHORT")

        assert sl_price_long == Decimal("44100")
        assert sl_price_short == Decimal("45900")


class TestCalculateTakeProfitPrice:
    """Tests for calculate_take_profit_price method."""

    def test_calculate_take_profit_long(self):
        """Test take profit price for long position."""
        entry = Decimal("45000")
        tp_pct = Decimal("0.05")  # 5%

        tp_price = RiskManagerService.calculate_take_profit_price(entry, tp_pct, "long")

        # 45000 × (1 + 0.05) = 47250
        assert tp_price == Decimal("47250")

    def test_calculate_take_profit_short(self):
        """Test take profit price for short position."""
        entry = Decimal("45000")
        tp_pct = Decimal("0.05")  # 5%

        tp_price = RiskManagerService.calculate_take_profit_price(entry, tp_pct, "short")

        # 45000 × (1 - 0.05) = 42750
        assert tp_price == Decimal("42750")

    def test_calculate_take_profit_case_insensitive(self):
        """Test take profit calculation is case insensitive."""
        entry = Decimal("45000")
        tp_pct = Decimal("0.05")

        tp_price_long = RiskManagerService.calculate_take_profit_price(entry, tp_pct, "LONG")
        tp_price_short = RiskManagerService.calculate_take_profit_price(entry, tp_pct, "SHORT")

        assert tp_price_long == Decimal("47250")
        assert tp_price_short == Decimal("42750")


class TestValidateCompleteDecision:
    """Tests for validate_complete_decision method."""

    @pytest.fixture
    def bot_for_complete_validation(self, test_bot):
        """Create a bot for complete validation tests."""
        test_bot.capital = Decimal("10000")
        test_bot.risk_params = {
            "max_position_pct": Decimal("0.25"),
            "max_drawdown_pct": Decimal("0.20"),
            "max_trades_per_day": 10,
        }
        return test_bot

    def test_validate_complete_decision_entry_passes_all_checks(self, bot_for_complete_validation):
        """Test complete validation passing all checks."""
        decision = {
            "action": "entry",
            "symbol": "BTC/USDT",
            "side": "long",
            "size_pct": Decimal("0.10"),
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("44000"),
            "take_profit": Decimal("47000"),
        }

        valid, msg = RiskManagerService.validate_complete_decision(
            bot_for_complete_validation,
            decision,
            [],
            Decimal("45000"),
            trades_today=3,
            portfolio_value=Decimal("10000"),
        )

        assert valid is True
        assert "All validations passed" in msg

    def test_validate_complete_decision_frequency_fails(self, bot_for_complete_validation):
        """Test complete validation fails on frequency check."""
        decision = {
            "action": "entry",
            "symbol": "BTC/USDT",
            "size_pct": Decimal("0.10"),
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("44000"),
            "take_profit": Decimal("47000"),
        }

        valid, msg = RiskManagerService.validate_complete_decision(
            bot_for_complete_validation,
            decision,
            [],
            Decimal("45000"),
            trades_today=10,  # At limit
            portfolio_value=Decimal("10000"),
        )

        assert valid is False
        assert "limit reached" in msg

    def test_validate_complete_decision_drawdown_fails(self, bot_for_complete_validation):
        """Test complete validation fails on drawdown check."""
        decision = {
            "action": "entry",
            "symbol": "BTC/USDT",
            "size_pct": Decimal("0.10"),
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("44000"),
            "take_profit": Decimal("47000"),
        }

        valid, msg = RiskManagerService.validate_complete_decision(
            bot_for_complete_validation,
            decision,
            [],
            Decimal("45000"),
            trades_today=3,
            portfolio_value=Decimal("7900"),  # 21% drawdown
        )

        assert valid is False
        assert "Drawdown" in msg

    def test_validate_complete_decision_entry_fails(self, bot_for_complete_validation):
        """Test complete validation fails on entry validation."""
        decision = {
            "action": "entry",
            "symbol": "BTC/USDT",
            "size_pct": Decimal("0.30"),  # Exceeds 0.25 max
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("44000"),
            "take_profit": Decimal("47000"),
        }

        valid, msg = RiskManagerService.validate_complete_decision(
            bot_for_complete_validation,
            decision,
            [],
            Decimal("45000"),
            trades_today=3,
            portfolio_value=Decimal("10000"),
        )

        assert valid is False
        assert "exceeds max" in msg

    def test_validate_complete_decision_non_entry_action(self, bot_for_complete_validation):
        """Test complete validation skips validation for non-entry actions."""
        decision = {
            "action": "exit",  # Not an entry
        }

        valid, msg = RiskManagerService.validate_complete_decision(
            bot_for_complete_validation,
            decision,
            [],
            Decimal("45000"),
            trades_today=3,
        )

        assert valid is True
        assert "No validation needed" in msg

    def test_validate_complete_decision_default_portfolio_value(self, bot_for_complete_validation):
        """Test complete validation uses bot capital when portfolio_value not provided."""
        decision = {
            "action": "entry",
            "symbol": "BTC/USDT",
            "size_pct": Decimal("0.10"),
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("44000"),
            "take_profit": Decimal("47000"),
        }

        # Should use bot.capital (10000) when portfolio_value=None
        valid, msg = RiskManagerService.validate_complete_decision(
            bot_for_complete_validation,
            decision,
            [],
            Decimal("45000"),
            trades_today=3,
            portfolio_value=None,
        )

        assert valid is True
