"""Tests for Execution Block - Trade execution and PnL."""

import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models.position import PositionSide


class TestMarginCalculation:
    """Test margin and notional calculations."""

    def test_margin_with_leverage(self):
        """Margin = capital * size_pct, Notional = margin * leverage."""
        capital = Decimal("10000")
        size_pct = Decimal("0.20")  # 20%
        leverage = Decimal("10")

        margin = capital * size_pct
        notional = margin * leverage

        assert margin == Decimal("2000")
        assert notional == Decimal("20000")

    def test_quantity_calculation(self):
        """Quantity = notional / entry_price."""
        notional = Decimal("20000")
        entry_price = Decimal("88000")  # BTC price

        quantity = notional / entry_price
        assert quantity == Decimal("20000") / Decimal("88000")
        # ~0.227 BTC

    def test_fees_calculation(self):
        """Fees = 0.1% of notional."""
        notional = Decimal("20000")
        fee_rate = Decimal("0.001")  # 0.1%

        fees = notional * fee_rate
        assert fees == Decimal("20")


class TestPnLCalculation:
    """Test PnL calculations for closing positions."""

    def test_long_profit(self):
        """LONG PnL = (exit - entry) * quantity."""
        entry_price = Decimal("88000")
        exit_price = Decimal("90000")
        quantity = Decimal("0.25")

        pnl = (exit_price - entry_price) * quantity
        assert pnl == Decimal("500")  # +$500 profit

    def test_long_loss(self):
        """LONG loss when price drops."""
        entry_price = Decimal("88000")
        exit_price = Decimal("85000")
        quantity = Decimal("0.25")

        pnl = (exit_price - entry_price) * quantity
        assert pnl == Decimal("-750")  # -$750 loss

    def test_short_profit(self):
        """SHORT PnL = (entry - exit) * quantity."""
        entry_price = Decimal("88000")
        exit_price = Decimal("85000")
        quantity = Decimal("0.25")

        pnl = (entry_price - exit_price) * quantity
        assert pnl == Decimal("750")  # +$750 profit

    def test_short_loss(self):
        """SHORT loss when price rises."""
        entry_price = Decimal("88000")
        exit_price = Decimal("90000")
        quantity = Decimal("0.25")

        pnl = (entry_price - exit_price) * quantity
        assert pnl == Decimal("-500")  # -$500 loss


class TestCapitalManagement:
    """Test capital updates on entry/exit."""

    def test_entry_deducts_margin_and_fees(self):
        """Entry: new_capital = capital - margin - fees."""
        capital = Decimal("10000")
        margin = Decimal("2000")
        fees = Decimal("20")

        new_capital = capital - margin - fees
        assert new_capital == Decimal("7980")

    def test_exit_returns_margin_plus_pnl_minus_fees(self):
        """Exit: new_capital = capital + margin + pnl - fees."""
        capital = Decimal("7980")  # After entry
        margin = Decimal("2000")
        pnl = Decimal("500")  # Profit
        fees = Decimal("20")

        new_capital = capital + margin + pnl - fees
        assert new_capital == Decimal("10460")  # $460 net profit

    def test_exit_with_loss(self):
        """Exit with loss: capital increases but less than margin."""
        capital = Decimal("7980")
        margin = Decimal("2000")
        pnl = Decimal("-500")  # Loss
        fees = Decimal("20")

        new_capital = capital + margin + pnl - fees
        assert new_capital == Decimal("9460")  # $540 net loss


class TestPositionSideEnum:
    """Test that PositionSide enum works correctly."""

    def test_position_side_values(self):
        """Verify PositionSide enum values."""
        # In this codebase, enum value == string (StrEnum behavior)
        assert PositionSide.LONG == "long"
        assert PositionSide.SHORT == "short"

    def test_enum_comparison(self):
        """Enum comparison works with both enum and string."""
        side = PositionSide.LONG

        # Both work due to StrEnum
        assert side == PositionSide.LONG
        assert side == "long"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
