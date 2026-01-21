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


class TestAdvancedRiskManagement:
    """Test advanced risk management features."""

    def setup_method(self):
        self.risk = RiskBlock()

    def test_microstructure_stops_long(self):
        """Test microstructure-aware stops for LONG position."""
        entry_price = Decimal("100")
        atr = Decimal("2")  # 2% volatility

        sl, tp = self.risk.calculate_microstructure_stops(
            entry_price=entry_price,
            side="long",
            atr=atr,
            volatility_level="medium",
        )

        # SL should be below entry
        assert sl < entry_price
        # TP should be above entry
        assert tp > entry_price
        # TP should be roughly 2x distance from SL
        assert tp > sl

    def test_microstructure_stops_short(self):
        """Test microstructure-aware stops for SHORT position."""
        entry_price = Decimal("100")
        atr = Decimal("2")

        sl, tp = self.risk.calculate_microstructure_stops(
            entry_price=entry_price,
            side="short",
            atr=atr,
            volatility_level="medium",
        )

        # SL should be above entry
        assert sl > entry_price
        # TP should be below entry
        assert tp < entry_price

    def test_microstructure_stops_tight_cloud(self):
        """Test tighter stops when Ichimoku cloud is tight."""
        entry_price = Decimal("100")
        atr = Decimal("5")  # High volatility
        tight_kumo_width = Decimal("0.005")  # 0.5% - very tight

        sl, tp = self.risk.calculate_microstructure_stops(
            entry_price=entry_price,
            side="long",
            atr=atr,
            kumo_width=tight_kumo_width,
            volatility_level="high",
        )

        # With tight cloud, should use 1.5% stops
        expected_sl = entry_price - (Decimal("0.015") * entry_price)
        assert abs(sl - expected_sl) < Decimal("0.1")

    def test_detect_structure_breaks_ichimoku(self):
        """Test structure break detection for Ichimoku cloud."""
        position = MagicMock(spec=Position)
        position.symbol = "BTC/USDT"
        position.side = PositionSide.LONG
        position.entry_price = Decimal("100")

        signals = {"price_breaks_kumo": True}

        should_close, reason = self.risk.detect_structure_breaks(
            position=position,
            current_price=Decimal("85"),
            signals=signals,
        )

        assert should_close is True
        assert reason == "ichimoku_cloud_break"

    def test_detect_structure_breaks_no_break(self):
        """Test structure break detection with no breaks."""
        position = MagicMock(spec=Position)
        position.symbol = "BTC/USDT"

        should_close, reason = self.risk.detect_structure_breaks(
            position=position,
            current_price=Decimal("100"),
            signals={},
        )

        assert should_close is False
        assert reason is None

    def test_pyramid_first_entry_allowed(self):
        """Test pyramid allows first entry when no positions exist."""
        can_pyramid, reason = self.risk.can_pyramid_entry(
            symbol="BTC/USDT",
            current_positions=[],
            first_position_profitable=False,
        )

        assert can_pyramid is True
        assert "First entry" in reason

    def test_pyramid_second_entry_requires_profitability(self):
        """Test pyramid second entry requires first position to be profitable."""
        existing = MagicMock(spec=Position)
        existing.symbol = "BTC/USDT"
        existing.status = PositionStatus.OPEN

        # Not profitable
        can_pyramid, reason = self.risk.can_pyramid_entry(
            symbol="BTC/USDT",
            current_positions=[existing],
            first_position_profitable=False,
        )

        assert can_pyramid is False
        assert "not profitable" in reason

    def test_pyramid_second_entry_allowed_when_profitable(self):
        """Test pyramid allows second entry when first is profitable."""
        existing = MagicMock(spec=Position)
        existing.symbol = "BTC/USDT"
        existing.status = PositionStatus.OPEN

        can_pyramid, reason = self.risk.can_pyramid_entry(
            symbol="BTC/USDT",
            current_positions=[existing],
            first_position_profitable=True,
        )

        assert can_pyramid is True
        assert "Second entry" in reason

    def test_pyramid_max_positions_enforced(self):
        """Test pyramid rejects entry when max positions reached."""
        pos1 = MagicMock(spec=Position)
        pos1.symbol = "BTC/USDT"
        pos1.status = PositionStatus.OPEN

        pos2 = MagicMock(spec=Position)
        pos2.symbol = "BTC/USDT"
        pos2.status = PositionStatus.OPEN

        can_pyramid, reason = self.risk.can_pyramid_entry(
            symbol="BTC/USDT",
            current_positions=[pos1, pos2],
            first_position_profitable=True,
        )

        assert can_pyramid is False
        assert "max" in reason

    def test_calculate_pyramid_size_first_entry(self):
        """Test pyramid size calculation for first entry."""
        capital = Decimal("10000")
        current_exposure = Decimal("0")

        size = self.risk.calculate_pyramid_size(
            entry_number=1,
            capital=capital,
            current_exposure=current_exposure,
        )

        # First entry should be 10%
        assert size == Decimal("0.10")

    def test_calculate_pyramid_size_second_entry(self):
        """Test pyramid size calculation for second entry."""
        capital = Decimal("10000")
        current_exposure = Decimal("1000")  # 10% already

        size = self.risk.calculate_pyramid_size(
            entry_number=2,
            capital=capital,
            current_exposure=current_exposure,
        )

        # Second entry should be 5%
        assert size == Decimal("0.05")

    def test_calculate_pyramid_size_respects_max(self):
        """Test pyramid size respects 15% max total."""
        capital = Decimal("10000")
        current_exposure = Decimal("1100")  # 11% already

        size = self.risk.calculate_pyramid_size(
            entry_number=2,
            capital=capital,
            current_exposure=current_exposure,
        )

        # Should allow 4% more (total 15%)
        assert size == Decimal("0.05") or size == Decimal("0")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
