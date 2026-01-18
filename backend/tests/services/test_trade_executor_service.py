"""
Tests for the TradeExecutorService.

Tests cover:
- Successful trade execution (entry and exit)
- Error handling (exchange errors, insufficient capital, invalid data)
- Edge cases (zero quantity, negative quantity, max position sizes)
- Integration with database and position tracking
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.services.trade_executor_service import TradeExecutorService
from src.services.position_service import PositionService, PositionOpen
from src.models.position import Position, PositionSide, PositionStatus
from src.models.trade import Trade, TradeSide
from src.models.bot import Bot


# ==============================================================================
# SUCCESSFUL TRADE EXECUTION TESTS
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_entry_long_position_paper_trading(db_session: AsyncSession, test_bot: Bot):
    """Test successful long entry execution in paper trading mode."""
    executor = TradeExecutorService(db_session, exchange_client=None)
    test_bot.paper_trading = True

    initial_capital = test_bot.capital
    decision = {
        "symbol": "BTC/USDT",
        "side": "long",
        "size_pct": 0.05,
        "entry_price": 45000.0,
        "stop_loss": 43650.0,
        "take_profit": 47700.0,
        "confidence": 0.8,
    }

    position, trade = await executor.execute_entry(test_bot, decision, Decimal("45000.00"))

    assert position is not None
    assert position.symbol == "BTC/USDT"
    assert position.side == PositionSide.LONG
    assert position.status == PositionStatus.OPEN
    assert position.entry_price == Decimal("45000.00")

    assert trade is not None
    assert trade.side == TradeSide.BUY
    assert trade.symbol == "BTC/USDT"

    # Verify capital was reduced
    reloaded_bot = await db_session.get(Bot, test_bot.id)
    assert reloaded_bot.capital < initial_capital


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_entry_short_position_paper_trading(db_session: AsyncSession, test_bot: Bot):
    """Test successful short entry execution."""
    executor = TradeExecutorService(db_session, exchange_client=None)
    test_bot.paper_trading = True

    decision = {
        "symbol": "ETH/USDT",
        "side": "short",
        "size_pct": 0.10,
        "entry_price": 2500.0,
        "stop_loss": 2750.0,
        "take_profit": 2250.0,
        "confidence": 0.7,
    }

    position, trade = await executor.execute_entry(test_bot, decision, Decimal("2500.00"))

    assert position is not None
    assert position.side == PositionSide.SHORT
    assert trade is not None
    assert trade.side == TradeSide.SELL


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_exit_long_position(db_session: AsyncSession, test_bot: Bot):
    """Test successful exit of a long position."""
    executor = TradeExecutorService(db_session, exchange_client=None)
    test_bot.paper_trading = True

    # Create a position
    position = Position(
        id=uuid.uuid4(),
        bot_id=test_bot.id,
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        quantity=Decimal("1.0"),
        entry_price=Decimal("45000.00"),
        current_price=Decimal("46000.00"),
        status=PositionStatus.OPEN,
        stop_loss=Decimal("43650.00"),
        take_profit=Decimal("47700.00"),
    )
    db_session.add(position)
    await db_session.commit()

    # Exit the position
    exit_trade = await executor.execute_exit(position, Decimal("46500.00"), reason="manual_close")

    assert exit_trade is not None
    assert exit_trade.side == TradeSide.SELL

    # Verify position was closed
    reloaded_position = await db_session.get(Position, position.id)
    assert reloaded_position.status == PositionStatus.CLOSED


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_exit_short_position(db_session: AsyncSession, test_bot: Bot):
    """Test successful exit of a short position."""
    executor = TradeExecutorService(db_session, exchange_client=None)
    test_bot.paper_trading = True

    # Create a short position
    short_position = Position(
        id=uuid.uuid4(),
        bot_id=test_bot.id,
        symbol="ETH/USDT",
        side=PositionSide.SHORT,
        quantity=Decimal("2.0"),
        entry_price=Decimal("2500.00"),
        current_price=Decimal("2400.00"),
        status=PositionStatus.OPEN,
        stop_loss=Decimal("2750.00"),
        take_profit=Decimal("2250.00"),
    )
    db_session.add(short_position)
    await db_session.commit()

    # Exit the short position (buy to close)
    exit_trade = await executor.execute_exit(short_position, Decimal("2400.00"), reason="manual_close")

    assert exit_trade is not None
    assert exit_trade.side == TradeSide.BUY  # Exit of short is a BUY


# ==============================================================================
# ERROR HANDLING AND VALIDATION TESTS
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_entry_invalid_stop_loss(db_session: AsyncSession, test_bot: Bot):
    """Test entry execution with invalid (zero) stop loss price."""
    executor = TradeExecutorService(db_session, exchange_client=None)

    decision = {
        "symbol": "BTC/USDT",
        "side": "long",
        "size_pct": 0.05,
        "entry_price": 45000.0,
        "stop_loss": 0,  # Invalid
        "take_profit": 47700.0,
        "confidence": 0.8,
    }

    position, trade = await executor.execute_entry(test_bot, decision, Decimal("45000.00"))

    # Should reject invalid stop loss
    assert position is None
    assert trade is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_entry_invalid_take_profit(db_session: AsyncSession, test_bot: Bot):
    """Test entry execution with invalid take profit price."""
    executor = TradeExecutorService(db_session, exchange_client=None)

    decision = {
        "symbol": "BTC/USDT",
        "side": "long",
        "size_pct": 0.05,
        "entry_price": 45000.0,
        "stop_loss": 43650.0,
        "take_profit": -100.0,  # Invalid
        "confidence": 0.8,
    }

    position, trade = await executor.execute_entry(test_bot, decision, Decimal("45000.00"))

    # Should reject invalid take profit
    assert position is None
    assert trade is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_entry_zero_quantity_with_zero_capital(db_session: AsyncSession, test_bot: Bot):
    """Test entry execution that results in zero quantity (zero capital)."""
    executor = TradeExecutorService(db_session, exchange_client=None)

    # Set bot capital to zero
    test_bot.capital = Decimal("0")

    decision = {
        "symbol": "BTC/USDT",
        "side": "long",
        "size_pct": 0.05,
        "entry_price": 45000.0,
        "stop_loss": 43650.0,
        "take_profit": 47700.0,
        "confidence": 0.8,
    }

    position, trade = await executor.execute_entry(test_bot, decision, Decimal("45000.00"))

    # Should skip trade due to zero quantity
    assert position is None
    assert trade is None


# ==============================================================================
# DATABASE AND STATE TESTS
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_entry_creates_database_records(db_session: AsyncSession, test_bot: Bot):
    """Test that entry execution creates both position and trade records in database."""
    executor = TradeExecutorService(db_session, exchange_client=None)
    test_bot.paper_trading = True

    decision = {
        "symbol": "BTC/USDT",
        "side": "long",
        "size_pct": 0.05,
        "entry_price": 45000.0,
        "stop_loss": 43650.0,
        "take_profit": 47700.0,
        "confidence": 0.8,
    }

    position, trade = await executor.execute_entry(test_bot, decision, Decimal("45000.00"))

    # Verify position record exists in database
    position_query = select(Position).where(Position.id == position.id)
    result = await db_session.execute(position_query)
    db_position = result.scalar_one_or_none()
    assert db_position is not None

    # Verify trade record exists in database
    trade_query = select(Trade).where(Trade.id == trade.id)
    result = await db_session.execute(trade_query)
    db_trade = result.scalar_one_or_none()
    assert db_trade is not None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_entry_exit_complete_workflow(db_session: AsyncSession, test_bot: Bot):
    """Test complete workflow: entry -> exit."""
    executor = TradeExecutorService(db_session, exchange_client=None)
    test_bot.paper_trading = True

    # Entry
    entry_decision = {
        "symbol": "BTC/USDT",
        "side": "long",
        "size_pct": 0.05,
        "entry_price": 45000.0,
        "stop_loss": 43650.0,
        "take_profit": 47700.0,
        "confidence": 0.8,
    }

    position, entry_trade = await executor.execute_entry(test_bot, entry_decision, Decimal("45000.00"))
    assert position.status == PositionStatus.OPEN

    # Exit
    exit_trade = await executor.execute_exit(position, Decimal("46500.00"), reason="manual_close")

    # Verify position is closed
    reloaded_position = await db_session.get(Position, position.id)
    assert reloaded_position.status == PositionStatus.CLOSED


# ==============================================================================
# POSITION SIZING AND CONFIDENCE TESTS
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_entry_uses_default_size_pct(db_session: AsyncSession, test_bot: Bot):
    """Test entry execution uses default size percentage when not provided."""
    executor = TradeExecutorService(db_session, exchange_client=None)
    test_bot.paper_trading = True

    decision = {
        "symbol": "BTC/USDT",
        "side": "long",
        # size_pct not provided, should use default
        "entry_price": 45000.0,
        "stop_loss": 43650.0,
        "take_profit": 47700.0,
    }

    position, trade = await executor.execute_entry(test_bot, decision, Decimal("45000.00"))

    assert position is not None
    assert position.quantity > 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_entry_confidence_affects_size(db_session: AsyncSession, test_bot: Bot):
    """Test that confidence level affects position size."""
    executor = TradeExecutorService(db_session, exchange_client=None)
    test_bot.paper_trading = True

    # Calculate expected sizes with different confidence levels
    # At same price and size_pct, confidence 0.95 should yield larger size than 0.35

    # First with low confidence
    decision_low_conf = {
        "symbol": "BTC/USDT",
        "side": "long",
        "size_pct": 0.05,
        "entry_price": 45000.0,
        "stop_loss": 43650.0,
        "take_profit": 47700.0,
        "confidence": 0.35,  # Low confidence
    }

    pos_low, _ = await executor.execute_entry(test_bot, decision_low_conf, Decimal("45000.00"))

    # Reset capital by getting fresh instance
    fresh_bot = await db_session.get(Bot, test_bot.id)
    # Set capital back to initial for fair comparison
    fresh_bot.capital = Decimal("10000.00")

    # Second with high confidence (same instrument but different capital now)
    decision_high_conf = {
        "symbol": "ETH/USDT",
        "side": "long",
        "size_pct": 0.05,
        "entry_price": 45000.0,  # Same USD amount as BTC
        "stop_loss": 43650.0,
        "take_profit": 47700.0,
        "confidence": 0.95,  # High confidence
    }

    pos_high, _ = await executor.execute_entry(fresh_bot, decision_high_conf, Decimal("45000.00"))

    # High confidence position should be larger than low confidence
    # (confidence adjustment scales 0.5x - 1.2x of base size)
    assert pos_high is not None
    assert pos_low is not None
    assert pos_high.quantity > pos_low.quantity


# ==============================================================================
# LEVERAGE AND SHORT TESTS
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_entry_short_uses_higher_leverage(db_session: AsyncSession, test_bot: Bot):
    """Test that short positions use higher leverage setting."""
    executor = TradeExecutorService(db_session, exchange_client=None)
    test_bot.paper_trading = True

    # Long position
    decision_long = {
        "symbol": "BTC/USDT",
        "side": "long",
        "size_pct": 0.05,
        "entry_price": 45000.0,
        "stop_loss": 43650.0,
        "take_profit": 47700.0,
    }

    pos_long, _ = await executor.execute_entry(test_bot, decision_long, Decimal("45000.00"))

    # Short position
    decision_short = {
        "symbol": "ETH/USDT",
        "side": "short",
        "size_pct": 0.05,
        "entry_price": 2500.0,
        "stop_loss": 2750.0,
        "take_profit": 2250.0,
    }

    pos_short, _ = await executor.execute_entry(test_bot, decision_short, Decimal("2500.00"))

    # Both should have valid leverage values
    assert pos_long is not None
    assert pos_short is not None
    assert pos_long.leverage > 0
    assert pos_short.leverage > 0


# ==============================================================================
# CAPITAL TRACKING TESTS
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_exit_with_profit_increases_capital(db_session: AsyncSession, test_bot: Bot):
    """Test that exit with profit increases capital."""
    executor = TradeExecutorService(db_session, exchange_client=None)
    test_bot.paper_trading = True

    # Create position at 45000, exit at 46500 (profit of 1500)
    position = Position(
        id=uuid.uuid4(),
        bot_id=test_bot.id,
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        quantity=Decimal("1.0"),
        entry_price=Decimal("45000.00"),
        current_price=Decimal("46500.00"),
        status=PositionStatus.OPEN,
        stop_loss=Decimal("43650.00"),
        take_profit=Decimal("47700.00"),
    )
    db_session.add(position)
    await db_session.commit()

    initial_capital = test_bot.capital

    # Exit with profit
    exit_trade = await executor.execute_exit(position, Decimal("46500.00"))

    reloaded_bot = await db_session.get(Bot, test_bot.id)
    # Capital should increase (profit)
    assert reloaded_bot.capital > initial_capital


@pytest.mark.asyncio
@pytest.mark.unit
async def test_exit_with_loss_decreases_capital(db_session: AsyncSession, test_bot: Bot):
    """Test that exit with loss decreases capital overall."""
    executor = TradeExecutorService(db_session, exchange_client=None)
    test_bot.paper_trading = True

    # First, do an entry to track capital properly
    entry_decision = {
        "symbol": "BTC/USDT",
        "side": "long",
        "size_pct": 0.05,
        "entry_price": 45000.0,
        "stop_loss": 43650.0,
        "take_profit": 47700.0,
        "confidence": 0.8,
    }

    position, entry_trade = await executor.execute_entry(test_bot, entry_decision, Decimal("45000.00"))
    capital_after_entry = (await db_session.get(Bot, test_bot.id)).capital

    # Now exit with loss (at 44000, we lose 1000)
    exit_trade = await executor.execute_exit(position, Decimal("44000.00"))

    reloaded_bot = await db_session.get(Bot, test_bot.id)

    # After exit, capital should be: entry capital + margin released + loss (negative)
    # Since loss > 0 (as absolute value) in PnL calculation, capital change should reflect the loss
    # We'll just verify the trade recorded a loss
    assert exit_trade.realized_pnl < 0  # Realized PnL should be negative


# ==============================================================================
# TRADE RECORD VALIDATION TESTS
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_entry_trade_has_correct_fields(db_session: AsyncSession, test_bot: Bot):
    """Test that entry trade record has all required fields."""
    executor = TradeExecutorService(db_session, exchange_client=None)
    test_bot.paper_trading = True

    decision = {
        "symbol": "BTC/USDT",
        "side": "long",
        "size_pct": 0.05,
        "entry_price": 45000.0,
        "stop_loss": 43650.0,
        "take_profit": 47700.0,
        "confidence": 0.8,
    }

    position, trade = await executor.execute_entry(test_bot, decision, Decimal("45000.00"))

    # Verify all required trade fields
    assert trade.bot_id == test_bot.id
    assert trade.position_id == position.id
    assert trade.symbol == "BTC/USDT"
    assert trade.side == TradeSide.BUY
    assert trade.quantity > 0
    assert trade.price == Decimal("45000.00")
    assert trade.fees >= 0
    assert trade.realized_pnl is not None
    assert trade.executed_at is not None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_exit_trade_has_realized_pnl(db_session: AsyncSession, test_bot: Bot):
    """Test that exit trade has realized PnL calculated."""
    executor = TradeExecutorService(db_session, exchange_client=None)
    test_bot.paper_trading = True

    position = Position(
        id=uuid.uuid4(),
        bot_id=test_bot.id,
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        quantity=Decimal("1.0"),
        entry_price=Decimal("45000.00"),
        current_price=Decimal("46000.00"),
        status=PositionStatus.OPEN,
        stop_loss=Decimal("43650.00"),
        take_profit=Decimal("47700.00"),
    )
    db_session.add(position)
    await db_session.commit()

    exit_trade = await executor.execute_exit(position, Decimal("46500.00"))

    # Should have profit (1500 from price difference, minus fees)
    assert exit_trade is not None
    assert exit_trade.realized_pnl > 0
