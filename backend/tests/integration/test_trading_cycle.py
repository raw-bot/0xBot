"""Integration tests for trading cycle workflows.

Tests complete trading workflows from market data fetch to execution and logging.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.bot import Bot, BotStatus, ModelName
from src.models.position import Position, PositionSide, PositionStatus
from src.models.trade import Trade, TradeSide
from src.services.market_data_service import MarketDataService
from src.services.market_analysis_service import MarketAnalysisService
from src.services.risk_manager_service import RiskManagerService
from src.services.trade_executor_service import TradeExecutorService
from src.services.position_service import PositionService


@pytest.mark.asyncio
@pytest.mark.integration
class TestTradingCycleIntegration:
    """Integration tests for complete trading cycles."""

    async def test_complete_trading_cycle(
        self,
        db_session: AsyncSession,
        test_bot: Bot,
        test_user,
        mock_exchange,
        mock_llm_client,
    ):
        """Test complete trading cycle: fetch data → analyze → decide → risk check → execute."""
        # Setup services
        market_data_service = MarketDataService(exchange=mock_exchange)
        market_analysis_service = MarketAnalysisService()
        risk_manager_service = RiskManagerService()
        trade_executor_service = TradeExecutorService(
            exchange=mock_exchange, db_session=db_session
        )
        position_service = PositionService(db_session=db_session)

        # Step 1: Fetch market data
        market_data = await market_data_service.get_market_snapshot("BTC/USDT")
        assert market_data is not None
        assert market_data.get("symbol") == "BTC/USDT"

        # Step 2: Analyze market
        prices = [45000, 45500, 46000, 46500, 47000]
        analysis = market_analysis_service.analyze_correlation(
            {"BTC/USDT": prices, "ETH/USDT": [2400, 2450, 2500, 2550, 2600]}
        )
        assert analysis is not None

        # Step 3: Risk validation
        decision = {
            "symbol": "BTC/USDT",
            "side": "long",
            "size_pct": 0.10,
            "entry_price": Decimal("47000"),
            "stop_loss": Decimal("45650"),
            "take_profit": Decimal("48810"),
            "confidence": 0.75,
        }
        is_valid, error = risk_manager_service.validate_entry(test_bot, decision)
        assert is_valid is True

        # Step 4: Execute trade
        execution_result = await trade_executor_service.execute_entry(
            test_bot, decision
        )
        assert execution_result is not None
        assert execution_result.position_id is not None

        # Step 5: Verify database state
        positions = await position_service.get_open_positions(test_bot.id)
        assert len(positions) > 0
        assert positions[0].symbol == "BTC/USDT"
        assert positions[0].status == PositionStatus.OPEN

    async def test_trading_cycle_with_multiple_positions(
        self,
        db_session: AsyncSession,
        test_bot: Bot,
        mock_exchange,
    ):
        """Test trading cycle managing multiple concurrent positions."""
        market_data_service = MarketDataService(exchange=mock_exchange)
        risk_manager_service = RiskManagerService()
        trade_executor_service = TradeExecutorService(
            exchange=mock_exchange, db_session=db_session
        )
        position_service = PositionService(db_session=db_session)

        # Create multiple positions
        symbols = ["BTC/USDT", "ETH/USDT"]
        decisions = []

        for symbol in symbols:
            decision = {
                "symbol": symbol,
                "side": "long",
                "size_pct": 0.08,
                "entry_price": Decimal("1000") if symbol == "ETH/USDT" else Decimal("45000"),
                "stop_loss": Decimal("970") if symbol == "ETH/USDT" else Decimal("43650"),
                "take_profit": Decimal("1040") if symbol == "ETH/USDT" else Decimal("46800"),
                "confidence": 0.70,
            }
            decisions.append(decision)

        # Execute all trades
        execution_results = []
        for decision in decisions:
            is_valid, _ = risk_manager_service.validate_entry(test_bot, decision)
            if is_valid:
                result = await trade_executor_service.execute_entry(test_bot, decision)
                execution_results.append(result)

        # Verify all positions created
        assert len(execution_results) == len(symbols)
        positions = await position_service.get_open_positions(test_bot.id)
        assert len(positions) == len(symbols)

        # Verify total exposure
        total_exposure = await position_service.get_total_exposure(test_bot.id)
        assert total_exposure > 0

    async def test_trading_cycle_exit_flow(
        self,
        db_session: AsyncSession,
        test_bot: Bot,
        mock_exchange,
    ):
        """Test trading cycle including entry and exit."""
        trade_executor_service = TradeExecutorService(
            exchange=mock_exchange, db_session=db_session
        )
        position_service = PositionService(db_session=db_session)

        # Open position
        entry_decision = {
            "symbol": "BTC/USDT",
            "side": "long",
            "size_pct": 0.10,
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("43650"),
            "take_profit": Decimal("47700"),
            "confidence": 0.75,
        }
        entry_result = await trade_executor_service.execute_entry(test_bot, entry_decision)
        position_id = entry_result.position_id

        # Verify position open
        position = await position_service.get_position(position_id)
        assert position.status == PositionStatus.OPEN
        initial_capital = test_bot.capital

        # Close position with profit
        exit_result = await trade_executor_service.execute_exit(
            test_bot, position_id, Decimal("46500")
        )
        assert exit_result is not None
        assert exit_result.realized_pnl > 0

        # Verify position closed
        position = await position_service.get_position(position_id)
        assert position.status == PositionStatus.CLOSED
        assert position.exit_price == Decimal("46500")

        # Verify capital increased from profit
        assert test_bot.capital > initial_capital

    async def test_trading_cycle_with_loss(
        self,
        db_session: AsyncSession,
        test_bot: Bot,
        mock_exchange,
    ):
        """Test trading cycle with loss-making exit."""
        trade_executor_service = TradeExecutorService(
            exchange=mock_exchange, db_session=db_session
        )
        position_service = PositionService(db_session=db_session)

        # Open position
        entry_decision = {
            "symbol": "BTC/USDT",
            "side": "long",
            "size_pct": 0.10,
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("43650"),
            "take_profit": Decimal("47700"),
            "confidence": 0.60,
        }
        entry_result = await trade_executor_service.execute_entry(test_bot, entry_decision)
        position_id = entry_result.position_id
        initial_capital = test_bot.capital

        # Exit at loss
        exit_result = await trade_executor_service.execute_exit(
            test_bot, position_id, Decimal("44000")
        )
        assert exit_result is not None
        assert exit_result.realized_pnl < 0

        # Verify capital decreased
        assert test_bot.capital < initial_capital

    async def test_trading_cycle_stop_loss_hit(
        self,
        db_session: AsyncSession,
        test_bot: Bot,
        mock_exchange,
    ):
        """Test trading cycle with stop loss triggered."""
        position_service = PositionService(db_session=db_session)

        # Create position
        position_data = {
            "bot_id": test_bot.id,
            "symbol": "BTC/USDT",
            "side": PositionSide.LONG,
            "quantity": Decimal("1.5"),
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("43650"),
            "take_profit": Decimal("47700"),
            "opened_at": datetime.utcnow(),
        }
        position = await position_service.open_position(position_data)

        # Update price to trigger stop loss
        await position_service.update_current_price(position.id, Decimal("43000"))

        # Check if stop loss is hit
        position = await position_service.get_position(position.id)
        sl_hit, tp_hit = await position_service.check_stop_loss_take_profit(
            position, Decimal("43000")
        )
        assert sl_hit is True
        assert tp_hit is False

    async def test_trading_cycle_take_profit_hit(
        self,
        db_session: AsyncSession,
        test_bot: Bot,
        mock_exchange,
    ):
        """Test trading cycle with take profit triggered."""
        position_service = PositionService(db_session=db_session)

        # Create position
        position_data = {
            "bot_id": test_bot.id,
            "symbol": "BTC/USDT",
            "side": PositionSide.LONG,
            "quantity": Decimal("1.5"),
            "entry_price": Decimal("45000"),
            "stop_loss": Decimal("43650"),
            "take_profit": Decimal("47700"),
            "opened_at": datetime.utcnow(),
        }
        position = await position_service.open_position(position_data)

        # Update price to trigger take profit
        await position_service.update_current_price(position.id, Decimal("48000"))

        # Check if take profit is hit
        position = await position_service.get_position(position.id)
        sl_hit, tp_hit = await position_service.check_stop_loss_take_profit(
            position, Decimal("48000")
        )
        assert sl_hit is False
        assert tp_hit is True
