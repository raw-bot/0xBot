"""Integration tests for bot lifecycle workflows.

Tests complete bot workflows from creation to execution and cleanup.
"""

import uuid
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.bot import Bot, BotStatus, ModelName
from src.models.user import User
from src.models.position import Position, PositionSide, PositionStatus
from src.models.equity_snapshot import EquitySnapshot
from src.services.position_service import PositionService
from src.services.trade_executor_service import TradeExecutorService


@pytest.mark.asyncio
@pytest.mark.integration
class TestBotLifecycleIntegration:
    """Integration tests for complete bot lifecycle."""

    async def test_bot_creation_and_initialization(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test bot creation and proper initialization."""
        # Create bot
        bot = Bot(
            id=uuid.uuid4(),
            user_id=test_user.id,
            name="lifecycle_test_bot",
            model_name=ModelName.CLAUDE_SONNET,
            initial_capital=Decimal("50000.00"),
            capital=Decimal("50000.00"),
            trading_symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
            risk_params={
                "max_position_pct": 0.15,
                "max_drawdown_pct": 0.25,
                "max_trades_per_day": 15,
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.06,
            },
            status=BotStatus.INACTIVE,
            paper_trading=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(bot)
        await db_session.commit()
        await db_session.refresh(bot)

        # Verify bot created
        result = await db_session.execute(select(Bot).where(Bot.id == bot.id))
        retrieved_bot = result.scalar_one_or_none()
        assert retrieved_bot is not None
        assert retrieved_bot.name == "lifecycle_test_bot"
        assert retrieved_bot.status == BotStatus.INACTIVE
        assert retrieved_bot.capital == Decimal("50000.00")

    async def test_bot_status_transitions(
        self,
        db_session: AsyncSession,
        test_bot: Bot,
    ):
        """Test bot status transitions through lifecycle."""
        # Start bot
        test_bot.status = BotStatus.RUNNING
        await db_session.commit()
        await db_session.refresh(test_bot)
        assert test_bot.status == BotStatus.RUNNING

        # Pause bot
        test_bot.status = BotStatus.PAUSED
        await db_session.commit()
        await db_session.refresh(test_bot)
        assert test_bot.status == BotStatus.PAUSED

        # Resume bot
        test_bot.status = BotStatus.RUNNING
        await db_session.commit()
        await db_session.refresh(test_bot)
        assert test_bot.status == BotStatus.RUNNING

        # Stop bot
        test_bot.status = BotStatus.STOPPED
        await db_session.commit()
        await db_session.refresh(test_bot)
        assert test_bot.status == BotStatus.STOPPED

    async def test_bot_with_positions_lifecycle(
        self,
        db_session: AsyncSession,
        test_bot: Bot,
    ):
        """Test bot lifecycle with open positions."""
        position_service = PositionService(db_session=db_session)

        # Create multiple positions
        position_ids = []
        for i, symbol in enumerate(["BTC/USDT", "ETH/USDT"]):
            position_data = {
                "bot_id": test_bot.id,
                "symbol": symbol,
                "side": PositionSide.LONG,
                "quantity": Decimal("1.0") + Decimal(i),
                "entry_price": Decimal("45000") if i == 0 else Decimal("2500"),
                "stop_loss": Decimal("43650") if i == 0 else Decimal("2425"),
                "take_profit": Decimal("47700") if i == 0 else Decimal("2650"),
                "opened_at": datetime.utcnow(),
            }
            position = await position_service.open_position(position_data)
            position_ids.append(position.id)

        # Verify positions created
        open_positions = await position_service.get_open_positions(test_bot.id)
        assert len(open_positions) == 2

        # Update bot status while positions open
        test_bot.status = BotStatus.RUNNING
        await db_session.commit()

        # Close positions
        for position_id in position_ids:
            await position_service.close_position(position_id, Decimal("46000"))

        # Verify positions closed
        open_positions = await position_service.get_open_positions(test_bot.id)
        assert len(open_positions) == 0

        # Verify all positions stored
        all_positions = await position_service.get_all_positions(test_bot.id, limit=100)
        assert len(all_positions) == 2

    async def test_bot_capital_tracking_through_trades(
        self,
        db_session: AsyncSession,
        test_bot: Bot,
        mock_exchange,
    ):
        """Test bot capital tracking through trading lifecycle."""
        trade_executor_service = TradeExecutorService(
            exchange=mock_exchange, db_session=db_session
        )
        position_service = PositionService(db_session=db_session)

        initial_capital = test_bot.capital

        # Execute multiple trades
        for i in range(3):
            symbol = "BTC/USDT" if i % 2 == 0 else "ETH/USDT"
            entry_price = Decimal("45000") if i % 2 == 0 else Decimal("2500")
            exit_price = entry_price + Decimal("1000") if i % 2 == 0 else entry_price + Decimal("100")

            decision = {
                "symbol": symbol,
                "side": "long",
                "size_pct": 0.05,
                "entry_price": entry_price,
                "stop_loss": entry_price - Decimal("2000" if i % 2 == 0 else "200"),
                "take_profit": exit_price,
                "confidence": 0.70,
            }

            # Enter trade
            entry_result = await trade_executor_service.execute_entry(test_bot, decision)
            capital_after_entry = test_bot.capital

            # Exit trade with profit
            exit_result = await trade_executor_service.execute_exit(
                test_bot, entry_result.position_id, exit_price
            )
            capital_after_exit = test_bot.capital

            # Capital should increase on profitable exit
            assert capital_after_exit > capital_after_entry

        # Overall capital should be greater than initial
        assert test_bot.capital > initial_capital

    async def test_bot_with_equity_snapshots(
        self,
        db_session: AsyncSession,
        test_bot: Bot,
    ):
        """Test bot equity tracking through snapshots."""
        # Create equity snapshots
        snapshots = []
        for i in range(5):
            snapshot = EquitySnapshot(
                id=uuid.uuid4(),
                bot_id=test_bot.id,
                total_value=Decimal("10500.00") + Decimal(i * 100),
                cash=Decimal("9000.00") + Decimal(i * 50),
                positions_value=Decimal("1500.00") + Decimal(i * 50),
                unrealized_pnl=Decimal("500.00") + Decimal(i * 50),
                realized_pnl=Decimal(i * 100),
                timestamp=datetime.utcnow(),
            )
            db_session.add(snapshot)
            snapshots.append(snapshot)

        await db_session.commit()

        # Verify snapshots created
        result = await db_session.execute(
            select(EquitySnapshot)
            .where(EquitySnapshot.bot_id == test_bot.id)
            .order_by(EquitySnapshot.timestamp)
        )
        retrieved_snapshots = result.scalars().all()
        assert len(retrieved_snapshots) == 5

        # Verify equity progression
        first_snapshot = retrieved_snapshots[0]
        last_snapshot = retrieved_snapshots[-1]
        assert last_snapshot.total_value > first_snapshot.total_value

    async def test_bot_reset_after_lifecycle(
        self,
        db_session: AsyncSession,
        test_bot: Bot,
    ):
        """Test bot reset and cleanup after lifecycle."""
        position_service = PositionService(db_session=db_session)

        # Create some positions
        for symbol in ["BTC/USDT", "ETH/USDT"]:
            position_data = {
                "bot_id": test_bot.id,
                "symbol": symbol,
                "side": PositionSide.LONG,
                "quantity": Decimal("1.0"),
                "entry_price": Decimal("45000") if symbol == "BTC/USDT" else Decimal("2500"),
                "stop_loss": Decimal("43650") if symbol == "BTC/USDT" else Decimal("2425"),
                "take_profit": Decimal("47700") if symbol == "BTC/USDT" else Decimal("2650"),
                "opened_at": datetime.utcnow(),
            }
            await position_service.open_position(position_data)

        # Verify positions exist
        open_positions = await position_service.get_open_positions(test_bot.id)
        assert len(open_positions) == 2

        # Close all positions for cleanup
        for position in open_positions:
            await position_service.close_position(position.id, Decimal("45000"))

        # Reset bot state
        test_bot.status = BotStatus.INACTIVE
        test_bot.capital = test_bot.initial_capital
        await db_session.commit()

        # Verify cleanup
        open_positions = await position_service.get_open_positions(test_bot.id)
        assert len(open_positions) == 0
        assert test_bot.status == BotStatus.INACTIVE
        assert test_bot.capital == test_bot.initial_capital

    async def test_multiple_bots_isolation(
        self,
        db_session: AsyncSession,
        test_user: User,
        mock_exchange,
    ):
        """Test lifecycle of multiple bots with proper data isolation."""
        trade_executor_service = TradeExecutorService(
            exchange=mock_exchange, db_session=db_session
        )
        position_service = PositionService(db_session=db_session)

        # Create two bots
        bot1 = Bot(
            id=uuid.uuid4(),
            user_id=test_user.id,
            name="bot1",
            model_name=ModelName.CLAUDE_SONNET,
            initial_capital=Decimal("10000.00"),
            capital=Decimal("10000.00"),
            trading_symbols=["BTC/USDT"],
            risk_params={
                "max_position_pct": 0.10,
                "max_drawdown_pct": 0.20,
                "max_trades_per_day": 10,
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.06,
            },
            status=BotStatus.INACTIVE,
            paper_trading=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        bot2 = Bot(
            id=uuid.uuid4(),
            user_id=test_user.id,
            name="bot2",
            model_name=ModelName.CLAUDE_SONNET,
            initial_capital=Decimal("20000.00"),
            capital=Decimal("20000.00"),
            trading_symbols=["ETH/USDT"],
            risk_params={
                "max_position_pct": 0.15,
                "max_drawdown_pct": 0.25,
                "max_trades_per_day": 15,
                "stop_loss_pct": 0.04,
                "take_profit_pct": 0.08,
            },
            status=BotStatus.INACTIVE,
            paper_trading=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add_all([bot1, bot2])
        await db_session.commit()

        # Trade on both bots
        for bot in [bot1, bot2]:
            decision = {
                "symbol": "BTC/USDT" if bot.name == "bot1" else "ETH/USDT",
                "side": "long",
                "size_pct": 0.10,
                "entry_price": Decimal("45000") if bot.name == "bot1" else Decimal("2500"),
                "stop_loss": Decimal("43650") if bot.name == "bot1" else Decimal("2425"),
                "take_profit": Decimal("47700") if bot.name == "bot1" else Decimal("2650"),
                "confidence": 0.75,
            }
            await trade_executor_service.execute_entry(bot, decision)

        # Verify isolation
        bot1_positions = await position_service.get_open_positions(bot1.id)
        bot2_positions = await position_service.get_open_positions(bot2.id)

        assert len(bot1_positions) == 1
        assert len(bot2_positions) == 1
        assert bot1_positions[0].symbol == "BTC/USDT"
        assert bot2_positions[0].symbol == "ETH/USDT"
