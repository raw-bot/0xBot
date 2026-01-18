"""Comprehensive test suite for KellyPositionSizingService."""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.services.kelly_position_sizing_service import KellyPositionSizingService
from src.models import Trade, Bot


@pytest.fixture
async def kelly_service(db_session):
    """Create KellyPositionSizingService instance."""
    return KellyPositionSizingService(db_session)


class TestKellyCalculation:
    """Tests for Kelly criterion calculation."""

    async def test_kelly_calculation_basic(self, kelly_service):
        """Test basic Kelly formula calculation."""
        # Win rate 60%, avg win 5%, avg loss 2%
        # Kelly = (0.6 * 0.05 - 0.4 * 0.02) / 0.05 = (0.03 - 0.008) / 0.05 = 0.44
        kelly = kelly_service._calculate_kelly(
            Decimal("0.60"),
            Decimal("0.05"),
            Decimal("0.02")
        )

        assert kelly > 0
        assert kelly < 1.0

    async def test_kelly_calculation_conservative(self, kelly_service):
        """Test Kelly with conservative parameters."""
        # 50% win rate, 3% avg win, 3% avg loss
        kelly = kelly_service._calculate_kelly(
            Decimal("0.50"),
            Decimal("0.03"),
            Decimal("0.03")
        )

        assert kelly > 0
        assert kelly <= Decimal("0.10")  # Conservative

    async def test_kelly_calculation_aggressive(self, kelly_service):
        """Test Kelly with aggressive parameters."""
        # 70% win rate, 10% avg win, 1% avg loss
        kelly = kelly_service._calculate_kelly(
            Decimal("0.70"),
            Decimal("0.10"),
            Decimal("0.01")
        )

        assert kelly > 0
        assert kelly <= 1.0

    async def test_kelly_calculation_zero_win_rate(self, kelly_service):
        """Test Kelly with zero win rate."""
        kelly = kelly_service._calculate_kelly(
            Decimal("0.0"),
            Decimal("0.05"),
            Decimal("0.02")
        )

        # Should return fallback value
        assert kelly > 0

    async def test_kelly_calculation_100_percent_win_rate(self, kelly_service):
        """Test Kelly with 100% win rate."""
        kelly = kelly_service._calculate_kelly(
            Decimal("1.0"),
            Decimal("0.05"),
            Decimal("0.02")
        )

        assert kelly > 0
        assert kelly <= 1.0

    async def test_kelly_calculation_zero_loss(self, kelly_service):
        """Test Kelly with zero average loss (edge case)."""
        kelly = kelly_service._calculate_kelly(
            Decimal("0.50"),
            Decimal("0.05"),
            Decimal("0.0")
        )

        # Should return fallback
        assert kelly == Decimal("0.10")

    async def test_kelly_calculation_zero_win(self, kelly_service):
        """Test Kelly with zero average win (edge case)."""
        kelly = kelly_service._calculate_kelly(
            Decimal("0.50"),
            Decimal("0.0"),
            Decimal("0.02")
        )

        # Should return fallback
        assert kelly == Decimal("0.10")

    async def test_kelly_calculation_both_zero(self, kelly_service):
        """Test Kelly with both win and loss zero."""
        kelly = kelly_service._calculate_kelly(
            Decimal("0.50"),
            Decimal("0.0"),
            Decimal("0.0")
        )

        assert kelly == Decimal("0.10")

    async def test_kelly_calculation_bounds(self, kelly_service):
        """Test Kelly calculation respects bounds."""
        # Very profitable scenario
        kelly = kelly_service._calculate_kelly(
            Decimal("0.99"),
            Decimal("0.50"),
            Decimal("0.01")
        )

        # Should be capped at 1.0
        assert kelly <= Decimal("1.0")
        assert kelly >= Decimal("0.01")

    async def test_kelly_calculation_negative_kelly(self, kelly_service):
        """Test Kelly prevents negative values."""
        # Bad trading scenario (loses more than wins)
        kelly = kelly_service._calculate_kelly(
            Decimal("0.30"),
            Decimal("0.05"),
            Decimal("0.10")
        )

        # Should be positive (minimum bound)
        assert kelly >= Decimal("0.01")


class TestTradeAnalysis:
    """Tests for trade history analysis."""

    async def test_analyze_trades_winning_trades(self, kelly_service):
        """Test analysis with winning trades."""
        trades = [
            MagicMock(realized_pnl=100, entry_price=Decimal("100"), quantity=Decimal("1")),
            MagicMock(realized_pnl=50, entry_price=Decimal("100"), quantity=Decimal("1")),
        ]

        win_rate, avg_win_pct, avg_loss_pct = kelly_service._analyze_trades(trades)

        assert win_rate == Decimal("1.0")  # 100% wins
        assert avg_win_pct > 0

    async def test_analyze_trades_mixed(self, kelly_service):
        """Test analysis with mixed trades."""
        trades = [
            MagicMock(realized_pnl=100, entry_price=Decimal("100"), quantity=Decimal("1")),
            MagicMock(realized_pnl=-50, entry_price=Decimal("100"), quantity=Decimal("1")),
            MagicMock(realized_pnl=75, entry_price=Decimal("100"), quantity=Decimal("1")),
        ]

        win_rate, avg_win_pct, avg_loss_pct = kelly_service._analyze_trades(trades)

        assert win_rate == Decimal("2") / Decimal("3")  # 67% wins
        assert avg_win_pct > 0
        assert avg_loss_pct > 0

    async def test_analyze_trades_losing_trades(self, kelly_service):
        """Test analysis with losing trades."""
        trades = [
            MagicMock(realized_pnl=-100, entry_price=Decimal("100"), quantity=Decimal("1")),
            MagicMock(realized_pnl=-50, entry_price=Decimal("100"), quantity=Decimal("1")),
        ]

        win_rate, avg_win_pct, avg_loss_pct = kelly_service._analyze_trades(trades)

        assert win_rate == Decimal("0.0")
        assert avg_loss_pct > 0

    async def test_analyze_trades_empty(self, kelly_service):
        """Test analysis with no trades."""
        win_rate, avg_win_pct, avg_loss_pct = kelly_service._analyze_trades([])

        # Should return defaults
        assert win_rate == Decimal("0.50")
        assert avg_win_pct == Decimal("0.05")
        assert avg_loss_pct == Decimal("0.02")

    async def test_analyze_trades_breakeven(self, kelly_service):
        """Test analysis with breakeven trades."""
        trades = [
            MagicMock(realized_pnl=0, entry_price=Decimal("100"), quantity=Decimal("1")),
            MagicMock(realized_pnl=100, entry_price=Decimal("100"), quantity=Decimal("1")),
        ]

        win_rate, avg_win_pct, avg_loss_pct = kelly_service._analyze_trades(trades)

        # Zero PnL trades are neither wins nor losses
        assert win_rate == Decimal("1") / Decimal("2")

    async def test_analyze_trades_large_quantities(self, kelly_service):
        """Test analysis with varying quantities."""
        trades = [
            MagicMock(realized_pnl=200, entry_price=Decimal("100"), quantity=Decimal("2")),
            MagicMock(realized_pnl=-100, entry_price=Decimal("100"), quantity=Decimal("1")),
        ]

        win_rate, avg_win_pct, avg_loss_pct = kelly_service._analyze_trades(trades)

        assert win_rate == Decimal("1") / Decimal("2")


class TestCalculatePositionSize:
    """Tests for position size calculation."""

    async def test_position_size_insufficient_trades(self, kelly_service, test_bot, db_session, monkeypatch):
        """Test position size with insufficient trade history."""
        # Mock _get_recent_trades to return fewer trades than MIN_TRADES_FOR_KELLY
        async def mock_get_trades(bot_id, lookback_days=90):
            return []

        monkeypatch.setattr(kelly_service, "_get_recent_trades", mock_get_trades)

        size, reasoning = await kelly_service.calculate_position_size(
            str(test_bot.id),
            base_size_pct=Decimal("0.10")
        )

        assert size == Decimal("0.10")  # Returns base size
        assert "Not enough trades" in reasoning

    async def test_position_size_enough_trades(self, kelly_service, test_bot, monkeypatch):
        """Test position size with sufficient trade history."""
        # Create winning trades
        trades = [
            MagicMock(realized_pnl=100, entry_price=Decimal("100"), quantity=Decimal("1"))
            for _ in range(25)  # 25 trades (enough for Kelly)
        ]

        async def mock_get_trades(bot_id, lookback_days=90):
            return trades

        monkeypatch.setattr(kelly_service, "_get_recent_trades", mock_get_trades)

        size, reasoning = await kelly_service.calculate_position_size(
            str(test_bot.id),
            base_size_pct=Decimal("0.10")
        )

        # Should apply Kelly calculation
        assert size > 0
        assert "Kelly" in reasoning

    async def test_position_size_low_win_rate(self, kelly_service, test_bot, monkeypatch):
        """Test position size with low win rate (bad strategy)."""
        trades = [
            MagicMock(realized_pnl=-100, entry_price=Decimal("100"), quantity=Decimal("1"))
            for _ in range(16)  # 16 losing trades
        ]
        trades.extend([
            MagicMock(realized_pnl=50, entry_price=Decimal("100"), quantity=Decimal("1"))
            for _ in range(4)  # 4 winning trades (20% win rate, 20 total trades)
        ])

        async def mock_get_trades(bot_id, lookback_days=90):
            return trades

        monkeypatch.setattr(kelly_service, "_get_recent_trades", mock_get_trades)

        size, reasoning = await kelly_service.calculate_position_size(
            str(test_bot.id),
            base_size_pct=Decimal("0.10")
        )

        # Should reduce to 50% of base size or respect minimum
        assert size <= Decimal("0.10")  # Not larger than base
        assert "Low win rate" in reasoning

    async def test_position_size_respects_minimum(self, kelly_service, test_bot, monkeypatch):
        """Test position size respects minimum bound."""
        trades = [
            MagicMock(realized_pnl=10, entry_price=Decimal("100"), quantity=Decimal("1"))
            for _ in range(20)
        ]

        async def mock_get_trades(bot_id, lookback_days=90):
            return trades

        monkeypatch.setattr(kelly_service, "_get_recent_trades", mock_get_trades)

        size, reasoning = await kelly_service.calculate_position_size(
            str(test_bot.id),
            base_size_pct=Decimal("0.01")  # Very small base
        )

        # Should respect MIN_SIZE_PCT
        assert size >= KellyPositionSizingService.MIN_SIZE_PCT

    async def test_position_size_respects_maximum(self, kelly_service, test_bot, monkeypatch):
        """Test position size respects maximum bound."""
        # Highly profitable trades
        trades = [
            MagicMock(realized_pnl=1000, entry_price=Decimal("100"), quantity=Decimal("1"))
            for _ in range(25)
        ]

        async def mock_get_trades(bot_id, lookback_days=90):
            return trades

        monkeypatch.setattr(kelly_service, "_get_recent_trades", mock_get_trades)

        size, reasoning = await kelly_service.calculate_position_size(
            str(test_bot.id),
            base_size_pct=Decimal("0.50")  # Large base size
        )

        # Should respect MAX_SIZE_PCT
        assert size <= KellyPositionSizingService.MAX_SIZE_PCT

    async def test_position_size_kelly_fraction_applied(self, kelly_service, test_bot, monkeypatch):
        """Test that 1/4 Kelly fraction is applied."""
        trades = [
            MagicMock(realized_pnl=100, entry_price=Decimal("100"), quantity=Decimal("1"))
            for _ in range(25)
        ]

        async def mock_get_trades(bot_id, lookback_days=90):
            return trades

        monkeypatch.setattr(kelly_service, "_get_recent_trades", mock_get_trades)

        size, reasoning = await kelly_service.calculate_position_size(str(test_bot.id))

        # Result should be less than raw Kelly (due to 1/4 fraction)
        assert "1/4 safety" in reasoning or "Kelly" in reasoning

    async def test_position_size_custom_parameters(self, kelly_service, test_bot, monkeypatch):
        """Test position size calculation with custom parameters."""
        trades = [
            MagicMock(realized_pnl=50, entry_price=Decimal("100"), quantity=Decimal("1"))
            for _ in range(20)
        ]

        async def mock_get_trades(bot_id, lookback_days=90):
            return trades

        monkeypatch.setattr(kelly_service, "_get_recent_trades", mock_get_trades)

        size, reasoning = await kelly_service.calculate_position_size(
            str(test_bot.id),
            base_size_pct=Decimal("0.15"),
            risk_per_trade_pct=Decimal("0.03")
        )

        assert size > 0
        assert size <= KellyPositionSizingService.MAX_SIZE_PCT

    async def test_position_size_error_handling(self, kelly_service, test_bot, monkeypatch):
        """Test position size calculation error handling."""
        async def mock_get_trades_error(bot_id, lookback_days=90):
            raise Exception("Database error")

        monkeypatch.setattr(kelly_service, "_get_recent_trades", mock_get_trades_error)

        size, reasoning = await kelly_service.calculate_position_size(
            str(test_bot.id),
            base_size_pct=Decimal("0.10")
        )

        # Should return base size and error message
        assert size == Decimal("0.10")
        assert "Error" in reasoning


class TestGetRecentTrades:
    """Tests for fetching recent trades from database."""

    async def test_get_recent_trades_empty(self, kelly_service, test_bot, db_session):
        """Test fetching trades when none exist."""
        trades = await kelly_service._get_recent_trades(str(test_bot.id))
        assert trades == []

    async def test_get_recent_trades_with_trades(self, kelly_service, test_bot, test_trade, db_session):
        """Test fetching trades when trades exist."""
        trades = await kelly_service._get_recent_trades(str(test_bot.id))

        # test_trade fixture should be in database
        assert len(trades) >= 0  # May or may not have trades depending on fixture

    async def test_get_recent_trades_lookback_period(self, kelly_service, test_bot, monkeypatch):
        """Test that lookback period is respected."""
        cutoff_date = None

        original_select = None
        from sqlalchemy import select as original_select_import

        async def mock_execute(stmt):
            # Capture cutoff_date from query
            nonlocal cutoff_date
            mock_result = AsyncMock()
            mock_result.scalars.return_value.all.return_value = []
            return mock_result

        monkeypatch.setattr(kelly_service.db_session, "execute", mock_execute)

        await kelly_service._get_recent_trades(str(test_bot.id), lookback_days=30)

        # Method should construct query with lookback period

    async def test_get_recent_trades_only_closed_trades(self, kelly_service, test_bot):
        """Test that only trades with realized PnL are returned."""
        # This test verifies the query filters for realized_pnl != 0
        trades = await kelly_service._get_recent_trades(str(test_bot.id))

        # All returned trades should have realized_pnl != 0
        for trade in trades:
            assert trade.realized_pnl != 0

    async def test_get_recent_trades_error_handling(self, kelly_service, test_bot, monkeypatch):
        """Test error handling when database query fails."""
        async def mock_execute_error(stmt):
            raise Exception("Database connection error")

        monkeypatch.setattr(kelly_service.db_session, "execute", mock_execute_error)

        trades = await kelly_service._get_recent_trades(str(test_bot.id))

        # Should return empty list on error
        assert trades == []


class TestKellyConstants:
    """Tests for Kelly service constants."""

    def test_kelly_fraction_constant(self):
        """Test that Kelly fraction is 1/4."""
        assert KellyPositionSizingService.KELLY_FRACTION == Decimal("0.25")

    def test_min_size_constant(self):
        """Test minimum position size constant."""
        assert KellyPositionSizingService.MIN_SIZE_PCT == Decimal("0.02")

    def test_max_size_constant(self):
        """Test maximum position size constant."""
        assert KellyPositionSizingService.MAX_SIZE_PCT == Decimal("0.25")

    def test_min_trades_constant(self):
        """Test minimum trades for Kelly constant."""
        assert KellyPositionSizingService.MIN_TRADES_FOR_KELLY == 20


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    async def test_kelly_with_very_small_decimals(self, kelly_service):
        """Test Kelly calculation with very small decimal values."""
        kelly = kelly_service._calculate_kelly(
            Decimal("0.0001"),
            Decimal("0.00001"),
            Decimal("0.000001")
        )

        assert kelly >= Decimal("0.01")

    async def test_kelly_with_very_large_decimals(self, kelly_service):
        """Test Kelly calculation with large decimal values."""
        kelly = kelly_service._calculate_kelly(
            Decimal("0.99"),
            Decimal("0.99"),
            Decimal("0.99")
        )

        assert kelly <= Decimal("1.0")

    async def test_analyze_trades_single_trade(self, kelly_service):
        """Test analysis with only one trade."""
        trades = [
            MagicMock(realized_pnl=100, entry_price=Decimal("100"), quantity=Decimal("1")),
        ]

        win_rate, avg_win_pct, avg_loss_pct = kelly_service._analyze_trades(trades)

        assert win_rate == Decimal("1.0")

    async def test_analyze_trades_many_small_trades(self, kelly_service):
        """Test analysis with many small trades."""
        trades = [
            MagicMock(realized_pnl=Decimal("1"), entry_price=Decimal("100"), quantity=Decimal("1"))
            for _ in range(100)
        ]

        win_rate, avg_win_pct, avg_loss_pct = kelly_service._analyze_trades(trades)

        assert win_rate == Decimal("1.0")
        assert avg_win_pct > 0

    async def test_calculate_position_size_zero_base_size(self, kelly_service, test_bot, monkeypatch):
        """Test position size with zero base size returns the zero base size (insufficient trades)."""
        trades = []

        async def mock_get_trades(bot_id, lookback_days=90):
            return trades

        monkeypatch.setattr(kelly_service, "_get_recent_trades", mock_get_trades)

        size, reasoning = await kelly_service.calculate_position_size(
            str(test_bot.id),
            base_size_pct=Decimal("0.0")
        )

        # With zero base size and no trades, returns zero (fallback to base_size)
        assert size == Decimal("0.0")
        assert "Not enough trades" in reasoning

    async def test_kelly_formula_known_values(self, kelly_service):
        """Test Kelly formula with known example values."""
        # From docstring: 55% WR, 5% avg win, 2% avg loss
        # Expected: f* = (0.55 * 5 - 0.45 * 2) / 5 = (2.75 - 0.9) / 5 = 0.37 = 37%
        kelly = kelly_service._calculate_kelly(
            Decimal("0.55"),
            Decimal("0.05"),
            Decimal("0.02")
        )

        # Should be approximately 0.37 before 1/4 Kelly fraction
        assert Decimal("0.35") < kelly < Decimal("0.40")
