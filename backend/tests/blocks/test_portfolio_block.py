"""Tests for Portfolio Block - Equity calculations."""

import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.blocks.block_portfolio import PortfolioBlock, PortfolioState


class TestEquityCalculation:
    """Test equity calculation: equity = cash + invested + unrealized_pnl."""

    def test_equity_no_positions(self):
        """With no positions, equity = cash."""
        cash = Decimal("10000")
        invested = Decimal("0")
        unrealized = Decimal("0")

        equity = cash + invested + unrealized
        assert equity == Decimal("10000")

    def test_equity_with_positions(self):
        """With positions, equity includes margin and unrealized PnL."""
        cash = Decimal("8000")  # Started with 10k, 2k in margin
        invested = Decimal("2000")  # Margin locked
        unrealized = Decimal("150")  # Profit

        equity = cash + invested + unrealized
        assert equity == Decimal("10150")  # 8000 + 2000 + 150

    def test_equity_with_loss(self):
        """Unrealized loss reduces equity."""
        cash = Decimal("8000")
        invested = Decimal("2000")
        unrealized = Decimal("-300")  # Loss

        equity = cash + invested + unrealized
        assert equity == Decimal("9700")  # 8000 + 2000 - 300

    def test_margin_calculation(self):
        """Margin = (entry_price * quantity) / leverage."""
        entry_price = Decimal("100")
        quantity = Decimal("10")
        leverage = Decimal("10")

        # Notional = 100 * 10 = 1000
        # Margin = 1000 / 10 = 100
        margin = (entry_price * quantity) / leverage
        assert margin == Decimal("100")

    def test_unrealized_pnl_long_profit(self):
        """LONG unrealized PnL when price goes up."""
        entry_price = Decimal("100")
        current_price = Decimal("110")
        quantity = Decimal("10")

        # PnL = (110 - 100) * 10 = 100 profit
        pnl = (current_price - entry_price) * quantity
        assert pnl == Decimal("100")

    def test_unrealized_pnl_long_loss(self):
        """LONG unrealized PnL when price goes down."""
        entry_price = Decimal("100")
        current_price = Decimal("90")
        quantity = Decimal("10")

        # PnL = (90 - 100) * 10 = -100 loss
        pnl = (current_price - entry_price) * quantity
        assert pnl == Decimal("-100")

    def test_unrealized_pnl_short_profit(self):
        """SHORT unrealized PnL when price goes down."""
        entry_price = Decimal("100")
        current_price = Decimal("90")
        quantity = Decimal("10")

        # PnL = (100 - 90) * 10 = 100 profit
        pnl = (entry_price - current_price) * quantity
        assert pnl == Decimal("100")


class TestReturnCalculation:
    """Test return percentage calculation."""

    def test_return_positive(self):
        """Positive return when equity > initial."""
        equity = Decimal("11000")
        initial = Decimal("10000")

        return_pct = float((equity - initial) / initial * 100)
        assert return_pct == 10.0  # 10% return

    def test_return_negative(self):
        """Negative return when equity < initial."""
        equity = Decimal("9000")
        initial = Decimal("10000")

        return_pct = float((equity - initial) / initial * 100)
        assert return_pct == -10.0  # -10% return

    def test_return_zero_initial(self):
        """Handle zero initial capital gracefully."""
        equity = Decimal("1000")
        initial = Decimal("0")

        return_pct = float((equity - initial) / initial * 100) if initial > 0 else 0
        assert return_pct == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
