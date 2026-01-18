"""Tests for position service."""

import pytest
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from src.services.position_service import PositionService, PositionOpen
from src.models.position import Position, PositionStatus, PositionSide


class TestPositionOpen:
    """Tests for PositionOpen data class."""

    def test_position_open_initialization(self):
        """Test PositionOpen initialization with all fields."""
        data = PositionOpen(
            symbol="BTC/USDT",
            side="long",
            quantity=Decimal("0.5"),
            entry_price=Decimal("45000"),
            stop_loss=Decimal("44000"),
            take_profit=Decimal("47000"),
            leverage=Decimal("2"),
            invalidation_condition="price > 48000",
        )

        assert data.symbol == "BTC/USDT"
        assert data.side == "long"
        assert data.quantity == Decimal("0.5")
        assert data.entry_price == Decimal("45000")
        assert data.stop_loss == Decimal("44000")
        assert data.take_profit == Decimal("47000")
        assert data.leverage == Decimal("2")
        assert data.invalidation_condition == "price > 48000"

    def test_position_open_minimal_initialization(self):
        """Test PositionOpen with minimal required fields."""
        data = PositionOpen(
            symbol="ETH/USDT",
            side="short",
            quantity=Decimal("1.0"),
            entry_price=Decimal("3000"),
        )

        assert data.symbol == "ETH/USDT"
        assert data.side == "short"
        assert data.quantity == Decimal("1.0")
        assert data.entry_price == Decimal("3000")
        assert data.stop_loss is None
        assert data.take_profit is None


class TestValidatePositionData:
    """Tests for position data validation."""

    @pytest.fixture
    def service(self, db_session):
        """Create a PositionService instance."""
        return PositionService(db_session)

    def test_validate_position_data_valid_long(self, service):
        """Test validation passes for valid long position."""
        data = PositionOpen(
            symbol="BTC/USDT",
            side="long",
            quantity=Decimal("0.5"),
            entry_price=Decimal("45000"),
        )

        # Should not raise
        service._validate_position_data(data)

    def test_validate_position_data_valid_short(self, service):
        """Test validation passes for valid short position."""
        data = PositionOpen(
            symbol="ETH/USDT",
            side="short",
            quantity=Decimal("1.0"),
            entry_price=Decimal("3000"),
        )

        service._validate_position_data(data)

    def test_validate_position_data_invalid_side(self, service):
        """Test validation fails for invalid side."""
        data = PositionOpen(
            symbol="BTC/USDT",
            side="invalid",
            quantity=Decimal("0.5"),
            entry_price=Decimal("45000"),
        )

        with pytest.raises(ValueError, match="Invalid side"):
            service._validate_position_data(data)

    def test_validate_position_data_zero_quantity(self, service):
        """Test validation fails for zero quantity."""
        data = PositionOpen(
            symbol="BTC/USDT",
            side="long",
            quantity=Decimal("0"),
            entry_price=Decimal("45000"),
        )

        with pytest.raises(ValueError, match="Quantity must be positive"):
            service._validate_position_data(data)

    def test_validate_position_data_negative_quantity(self, service):
        """Test validation fails for negative quantity."""
        data = PositionOpen(
            symbol="BTC/USDT",
            side="long",
            quantity=Decimal("-1"),
            entry_price=Decimal("45000"),
        )

        with pytest.raises(ValueError, match="Quantity must be positive"):
            service._validate_position_data(data)

    def test_validate_position_data_zero_entry_price(self, service):
        """Test validation fails for zero entry price."""
        data = PositionOpen(
            symbol="BTC/USDT",
            side="long",
            quantity=Decimal("0.5"),
            entry_price=Decimal("0"),
        )

        with pytest.raises(ValueError, match="Entry price must be positive"):
            service._validate_position_data(data)

    def test_validate_position_data_negative_entry_price(self, service):
        """Test validation fails for negative entry price."""
        data = PositionOpen(
            symbol="BTC/USDT",
            side="long",
            quantity=Decimal("0.5"),
            entry_price=Decimal("-100"),
        )

        with pytest.raises(ValueError, match="Entry price must be positive"):
            service._validate_position_data(data)

    def test_validate_position_data_zero_stop_loss(self, service):
        """Test validation fails for zero stop loss."""
        data = PositionOpen(
            symbol="BTC/USDT",
            side="long",
            quantity=Decimal("0.5"),
            entry_price=Decimal("45000"),
            stop_loss=Decimal("0"),
        )

        with pytest.raises(ValueError, match="Stop loss must be positive"):
            service._validate_position_data(data)

    def test_validate_position_data_zero_take_profit(self, service):
        """Test validation fails for zero take profit."""
        data = PositionOpen(
            symbol="BTC/USDT",
            side="long",
            quantity=Decimal("0.5"),
            entry_price=Decimal("45000"),
            take_profit=Decimal("0"),
        )

        with pytest.raises(ValueError, match="Take profit must be positive"):
            service._validate_position_data(data)


class TestOpenPosition:
    """Tests for open_position method."""

    @pytest.mark.asyncio
    async def test_open_position_long(self, db_session, test_bot):
        """Test opening a long position."""
        service = PositionService(db_session)
        data = PositionOpen(
            symbol="BTC/USDT",
            side="long",
            quantity=Decimal("0.5"),
            entry_price=Decimal("45000"),
            stop_loss=Decimal("44000"),
            take_profit=Decimal("47000"),
        )

        position = await service.open_position(test_bot.id, data)

        assert position.bot_id == test_bot.id
        assert position.symbol == "BTC/USDT"
        assert position.side == "long"
        assert position.quantity == Decimal("0.5")
        assert position.entry_price == Decimal("45000")
        assert position.current_price == Decimal("45000")
        assert position.stop_loss == Decimal("44000")
        assert position.take_profit == Decimal("47000")
        assert position.status == PositionStatus.OPEN
        assert position.opened_at is not None

    @pytest.mark.asyncio
    async def test_open_position_short(self, db_session, test_bot):
        """Test opening a short position."""
        service = PositionService(db_session)
        data = PositionOpen(
            symbol="ETH/USDT",
            side="short",
            quantity=Decimal("1.0"),
            entry_price=Decimal("3000"),
        )

        position = await service.open_position(test_bot.id, data)

        assert position.side == "short"
        assert position.symbol == "ETH/USDT"

    @pytest.mark.asyncio
    async def test_open_position_invalid_data(self, db_session, test_bot):
        """Test opening position with invalid data."""
        service = PositionService(db_session)
        data = PositionOpen(
            symbol="BTC/USDT",
            side="invalid",
            quantity=Decimal("0.5"),
            entry_price=Decimal("45000"),
        )

        with pytest.raises(ValueError, match="Invalid side"):
            await service.open_position(test_bot.id, data)


class TestClosePosition:
    """Tests for close_position method."""

    @pytest.mark.asyncio
    async def test_close_position_success(self, db_session, test_bot, test_position):
        """Test successfully closing a position."""
        service = PositionService(db_session)

        closed = await service.close_position(test_position.id, Decimal("46000"), "manual_close")

        assert closed.id == test_position.id
        assert closed.current_price == Decimal("46000")
        assert closed.status == PositionStatus.CLOSED
        assert closed.closed_at is not None

    @pytest.mark.asyncio
    async def test_close_position_not_found(self, db_session):
        """Test closing non-existent position."""
        service = PositionService(db_session)
        fake_id = uuid4()

        result = await service.close_position(fake_id, Decimal("46000"))

        assert result is None

    @pytest.mark.asyncio
    async def test_close_position_already_closed(self, db_session, test_bot):
        """Test closing an already closed position."""
        service = PositionService(db_session)

        # Create and close a position
        data = PositionOpen(
            symbol="BTC/USDT",
            side="long",
            quantity=Decimal("0.5"),
            entry_price=Decimal("45000"),
        )
        position = await service.open_position(test_bot.id, data)
        await service.close_position(position.id, Decimal("46000"))

        # Try to close again
        with pytest.raises(ValueError, match="already closed"):
            await service.close_position(position.id, Decimal("47000"))

    @pytest.mark.asyncio
    async def test_close_position_invalid_price(self, db_session, test_position):
        """Test closing with invalid exit price."""
        service = PositionService(db_session)

        with pytest.raises(ValueError, match="Exit price must be positive"):
            await service.close_position(test_position.id, Decimal("0"))


class TestUpdateCurrentPrice:
    """Tests for update_current_price method."""

    @pytest.mark.asyncio
    async def test_update_current_price_success(self, db_session, test_position):
        """Test successfully updating position price."""
        service = PositionService(db_session)

        updated = await service.update_current_price(test_position.id, Decimal("46000"))

        assert updated.id == test_position.id
        assert updated.current_price == Decimal("46000")
        assert updated.status == PositionStatus.OPEN

    @pytest.mark.asyncio
    async def test_update_current_price_not_found(self, db_session):
        """Test updating non-existent position."""
        service = PositionService(db_session)
        fake_id = uuid4()

        result = await service.update_current_price(fake_id, Decimal("46000"))

        assert result is None

    @pytest.mark.asyncio
    async def test_update_current_price_closed_position(self, db_session, test_bot):
        """Test updating price of closed position fails."""
        service = PositionService(db_session)

        # Create and close a position
        data = PositionOpen(
            symbol="BTC/USDT",
            side="long",
            quantity=Decimal("0.5"),
            entry_price=Decimal("45000"),
        )
        position = await service.open_position(test_bot.id, data)
        await service.close_position(position.id, Decimal("46000"))

        # Try to update price
        with pytest.raises(ValueError, match="Cannot update price of closed position"):
            await service.update_current_price(position.id, Decimal("47000"))

    @pytest.mark.asyncio
    async def test_update_current_price_invalid_price(self, db_session, test_position):
        """Test updating with invalid price."""
        service = PositionService(db_session)

        with pytest.raises(ValueError, match="Price must be positive"):
            await service.update_current_price(test_position.id, Decimal("-100"))


class TestGetPosition:
    """Tests for get_position method."""

    @pytest.mark.asyncio
    async def test_get_position_found(self, db_session, test_position):
        """Test getting an existing position."""
        service = PositionService(db_session)

        position = await service.get_position(test_position.id)

        assert position is not None
        assert position.id == test_position.id
        assert position.symbol == test_position.symbol

    @pytest.mark.asyncio
    async def test_get_position_not_found(self, db_session):
        """Test getting non-existent position."""
        service = PositionService(db_session)
        fake_id = uuid4()

        position = await service.get_position(fake_id)

        assert position is None


class TestGetOpenPositions:
    """Tests for get_open_positions method."""

    @pytest.mark.asyncio
    async def test_get_open_positions_single_bot(self, db_session, test_bot, test_position):
        """Test getting open positions for a bot."""
        service = PositionService(db_session)

        positions = await service.get_open_positions(test_bot.id)

        assert len(positions) >= 1
        assert any(p.id == test_position.id for p in positions)
        assert all(p.status == PositionStatus.OPEN for p in positions)

    @pytest.mark.asyncio
    async def test_get_open_positions_filter_by_symbol(self, db_session, test_bot, test_position):
        """Test getting open positions filtered by symbol."""
        service = PositionService(db_session)

        positions = await service.get_open_positions(test_bot.id, symbol=test_position.symbol)

        assert len(positions) >= 1
        assert all(p.symbol == test_position.symbol for p in positions)

    @pytest.mark.asyncio
    async def test_get_open_positions_symbol_not_found(self, db_session, test_bot):
        """Test getting positions for non-existent symbol."""
        service = PositionService(db_session)

        positions = await service.get_open_positions(test_bot.id, symbol="NONEXISTENT/USDT")

        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_get_open_positions_excludes_closed(self, db_session, test_bot, test_position):
        """Test that get_open_positions excludes closed positions."""
        service = PositionService(db_session)

        # Close the position
        await service.close_position(test_position.id, Decimal("50000"))

        # Get open positions
        positions = await service.get_open_positions(test_bot.id)

        assert all(p.status == PositionStatus.OPEN for p in positions)
        assert not any(p.id == test_position.id for p in positions)


class TestGetAllPositions:
    """Tests for get_all_positions method."""

    @pytest.mark.asyncio
    async def test_get_all_positions_with_count(self, db_session, test_bot, test_position):
        """Test getting all positions with total count."""
        service = PositionService(db_session)

        positions, total = await service.get_all_positions(test_bot.id)

        assert len(positions) >= 1
        assert total >= 1
        assert any(p.id == test_position.id for p in positions)

    @pytest.mark.asyncio
    async def test_get_all_positions_pagination(self, db_session, test_bot, test_position):
        """Test pagination of all positions."""
        service = PositionService(db_session)

        # Get first page
        positions1, total = await service.get_all_positions(test_bot.id, limit=1, offset=0)

        assert len(positions1) <= 1
        assert total >= 1

    @pytest.mark.asyncio
    async def test_get_all_positions_includes_closed(self, db_session, test_bot, test_position):
        """Test that get_all_positions includes closed positions."""
        service = PositionService(db_session)

        # Close the position
        await service.close_position(test_position.id, Decimal("50000"))

        # Get all positions
        positions, total = await service.get_all_positions(test_bot.id)

        assert any(p.id == test_position.id for p in positions)


class TestCheckStopLossTakeProfit:
    """Tests for check_stop_loss_take_profit method."""

    @pytest.mark.asyncio
    async def test_long_position_stop_loss_hit(self, db_session, test_position):
        """Test long position with stop loss hit."""
        test_position.side = PositionSide.LONG
        test_position.stop_loss = Decimal("44000")
        test_position.entry_price = Decimal("45000")

        service = PositionService(db_session)
        result = await service.check_stop_loss_take_profit(test_position, Decimal("43000"))

        assert result == "stop_loss"

    @pytest.mark.asyncio
    async def test_long_position_take_profit_hit(self, db_session, test_position):
        """Test long position with take profit hit."""
        test_position.side = PositionSide.LONG
        test_position.take_profit = Decimal("47000")
        test_position.entry_price = Decimal("45000")

        service = PositionService(db_session)
        result = await service.check_stop_loss_take_profit(test_position, Decimal("48000"))

        assert result == "take_profit"

    @pytest.mark.asyncio
    async def test_short_position_stop_loss_hit(self, db_session, test_position):
        """Test short position with stop loss hit."""
        test_position.side = PositionSide.SHORT
        test_position.stop_loss = Decimal("46000")
        test_position.entry_price = Decimal("45000")

        service = PositionService(db_session)
        result = await service.check_stop_loss_take_profit(test_position, Decimal("47000"))

        assert result == "stop_loss"

    @pytest.mark.asyncio
    async def test_short_position_take_profit_hit(self, db_session, test_position):
        """Test short position with take profit hit."""
        test_position.side = PositionSide.SHORT
        test_position.take_profit = Decimal("43000")
        test_position.entry_price = Decimal("45000")

        service = PositionService(db_session)
        result = await service.check_stop_loss_take_profit(test_position, Decimal("42000"))

        assert result == "take_profit"

    @pytest.mark.asyncio
    async def test_position_no_hit_long(self, db_session, test_position):
        """Test long position with no hit."""
        test_position.side = PositionSide.LONG
        test_position.stop_loss = Decimal("44000")
        test_position.take_profit = Decimal("47000")
        test_position.entry_price = Decimal("45000")

        service = PositionService(db_session)
        result = await service.check_stop_loss_take_profit(test_position, Decimal("45500"))

        assert result is None

    @pytest.mark.asyncio
    async def test_position_closed_no_check(self, db_session, test_position):
        """Test that closed positions are not checked."""
        test_position.status = PositionStatus.CLOSED
        test_position.side = PositionSide.LONG
        test_position.stop_loss = Decimal("44000")

        service = PositionService(db_session)
        result = await service.check_stop_loss_take_profit(test_position, Decimal("43000"))

        assert result is None

    @pytest.mark.asyncio
    async def test_position_no_stop_loss(self, db_session, test_position):
        """Test position without stop loss."""
        test_position.side = PositionSide.LONG
        test_position.stop_loss = None
        test_position.take_profit = Decimal("47000")

        service = PositionService(db_session)
        result = await service.check_stop_loss_take_profit(test_position, Decimal("43000"))

        # Should not return "stop_loss" even if it would be hit
        assert result is None or result == "take_profit"


class TestGetTotalExposure:
    """Tests for get_total_exposure method."""

    @pytest.mark.asyncio
    async def test_get_total_exposure_single_position(self, db_session, test_bot, test_position):
        """Test total exposure with single position."""
        service = PositionService(db_session)

        exposure = await service.get_total_exposure(test_bot.id)

        # Exposure = current_price × quantity
        expected = test_position.current_price * test_position.quantity
        assert exposure == expected

    @pytest.mark.asyncio
    async def test_get_total_exposure_no_positions(self, db_session, test_bot):
        """Test total exposure with no open positions."""
        service = PositionService(db_session)
        fake_bot_id = uuid4()

        exposure = await service.get_total_exposure(fake_bot_id)

        assert exposure == Decimal("0")
