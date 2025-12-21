"""Tests for the Risk Block - Critical for SL/TP validation."""

import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.blocks.block_risk import RiskBlock, ValidationResult
from src.models.position import Position, PositionSide, PositionStatus


class TestRiskBlockExitConditions:
    """Test SL/TP exit condition detection."""

    def setup_method(self):
        """Setup test fixtures."""
        self.risk = RiskBlock()

    def _create_mock_position(
        self,
        symbol: str,
        side: PositionSide,
        entry_price: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal,
    ) -> MagicMock:
        """Create a mock position for testing."""
        pos = MagicMock(spec=Position)
        pos.symbol = symbol
        pos.side = side
        pos.entry_price = entry_price
        pos.stop_loss = stop_loss
        pos.take_profit = take_profit
        pos.status = PositionStatus.OPEN
        return pos

    def test_long_stop_loss_triggered(self):
        """LONG position: SL should trigger when price <= stop_loss."""
        position = self._create_mock_position(
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            entry_price=Decimal("100"),
            stop_loss=Decimal("95"),
            take_profit=Decimal("110"),
        )

        # Price hits stop loss
        should_exit, reason = self.risk.check_exit_conditions(position, Decimal("95"))
        assert should_exit is True
        assert reason == "stop_loss"

        # Price below stop loss
        should_exit, reason = self.risk.check_exit_conditions(position, Decimal("90"))
        assert should_exit is True
        assert reason == "stop_loss"

    def test_long_take_profit_triggered(self):
        """LONG position: TP should trigger when price >= take_profit."""
        position = self._create_mock_position(
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            entry_price=Decimal("100"),
            stop_loss=Decimal("95"),
            take_profit=Decimal("110"),
        )

        # Price hits take profit
        should_exit, reason = self.risk.check_exit_conditions(position, Decimal("110"))
        assert should_exit is True
        assert reason == "take_profit"

        # Price above take profit
        should_exit, reason = self.risk.check_exit_conditions(position, Decimal("120"))
        assert should_exit is True
        assert reason == "take_profit"

    def test_long_no_exit(self):
        """LONG position: No exit when price is between SL and TP."""
        position = self._create_mock_position(
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            entry_price=Decimal("100"),
            stop_loss=Decimal("95"),
            take_profit=Decimal("110"),
        )

        # Price in middle
        should_exit, reason = self.risk.check_exit_conditions(position, Decimal("100"))
        assert should_exit is False
        assert reason == ""

    def test_short_stop_loss_triggered(self):
        """SHORT position: SL should trigger when price >= stop_loss."""
        position = self._create_mock_position(
            symbol="BTC/USDT",
            side=PositionSide.SHORT,
            entry_price=Decimal("100"),
            stop_loss=Decimal("105"),  # SL above entry for SHORT
            take_profit=Decimal("90"),  # TP below entry for SHORT
        )

        # Price hits stop loss
        should_exit, reason = self.risk.check_exit_conditions(position, Decimal("105"))
        assert should_exit is True
        assert reason == "stop_loss"

    def test_short_take_profit_triggered(self):
        """SHORT position: TP should trigger when price <= take_profit."""
        position = self._create_mock_position(
            symbol="BTC/USDT",
            side=PositionSide.SHORT,
            entry_price=Decimal("100"),
            stop_loss=Decimal("105"),
            take_profit=Decimal("90"),
        )

        # Price hits take profit
        should_exit, reason = self.risk.check_exit_conditions(position, Decimal("90"))
        assert should_exit is True
        assert reason == "take_profit"


class TestRiskBlockEntryValidation:
    """Test entry validation logic."""

    def setup_method(self):
        self.risk = RiskBlock(
            max_position_pct=0.25,
            max_exposure_pct=0.95,
            min_risk_reward=1.3,
        )

    def test_position_size_too_large(self):
        """Reject positions larger than max_position_pct."""
        result = self.risk.validate_entry(
            symbol="BTC/USDT",
            side="long",
            size_pct=0.50,  # 50% > 25% max
            entry_price=Decimal("100"),
            stop_loss=Decimal("95"),
            take_profit=Decimal("110"),
            capital=Decimal("10000"),
            current_positions=[],
        )
        assert result.is_valid is False
        assert "exceeds max" in result.reason

    def test_already_have_position(self):
        """Reject entry if already have position in same symbol."""
        existing = MagicMock()
        existing.symbol = "BTC/USDT"
        existing.status = PositionStatus.OPEN

        result = self.risk.validate_entry(
            symbol="BTC/USDT",
            side="long",
            size_pct=0.10,
            entry_price=Decimal("100"),
            stop_loss=Decimal("95"),
            take_profit=Decimal("110"),
            capital=Decimal("10000"),
            current_positions=[existing],
        )
        assert result.is_valid is False
        assert "Already have position" in result.reason

    def test_valid_long_entry(self):
        """Accept valid LONG entry."""
        result = self.risk.validate_entry(
            symbol="BTC/USDT",
            side="long",
            size_pct=0.10,
            entry_price=Decimal("100"),
            stop_loss=Decimal("95"),  # 5% SL
            take_profit=Decimal("110"),  # 10% TP -> R/R = 2.0
            capital=Decimal("10000"),
            current_positions=[],
        )
        assert result.is_valid is True

    def test_invalid_sl_tp_relationship_long(self):
        """LONG: Reject if SL >= entry or TP <= entry."""
        result = self.risk.validate_entry(
            symbol="BTC/USDT",
            side="long",
            size_pct=0.10,
            entry_price=Decimal("100"),
            stop_loss=Decimal("105"),  # SL above entry - INVALID
            take_profit=Decimal("110"),
            capital=Decimal("10000"),
            current_positions=[],
        )
        assert result.is_valid is False
        assert "Invalid LONG" in result.reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
