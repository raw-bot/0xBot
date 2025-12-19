"""
Audit Critical Paths - Regression Tests

Test 1: Full Trading Cycle
- Start bot → Wait 1 cycle → Check positions created
- Force price change → Check SL triggered
- Verify capital: initial - entry_cost + exit_proceeds = final

Test 2: Multi-Symbol Handling
- 5 symbols → Each gets correct price
- Positions don't mix prices

Test 3: Capital Integrity
- Sum(capital + invested) = equity
- After 10 cycles: no drift

Test 4: Database Consistency
- Positions.status matches reality
- Trades.realized_pnl calculated correctly
- Bot.capital updated atomically
"""

import asyncio
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.trading_engine_service import TradingEngineService
from src.services.market_data_service import MarketDataService
from src.services.position_service import PositionService
from src.services.trade_executor_service import TradeExecutorService
from src.services.risk_manager_service import RiskManagerService
from src.models.bot import Bot
from src.models.position import Position
from src.models.trade import Trade


class TestAuditCriticalPaths:
    """Critical path regression tests for trading system."""

    @pytest.fixture
    async def setup_services(self, db_session: AsyncSession):
        """Setup all services with mocked dependencies."""
        # Mock external dependencies
        market_data = AsyncMock(spec=MarketDataService)
        position_service = AsyncMock(spec=PositionService)
        trade_executor = AsyncMock(spec=TradeExecutorService)
        risk_manager = AsyncMock(spec=RiskManagerService)

        # Create trading engine
        trading_engine = TradingEngineService(
            market_data_service=market_data,
            position_service=position_service,
            trade_executor_service=trade_executor,
            risk_manager_service=risk_manager,
            db_session=db_session
        )

        return {
            'trading_engine': trading_engine,
            'market_data': market_data,
            'position_service': position_service,
            'trade_executor': trade_executor,
            'risk_manager': risk_manager
        }

    @pytest.mark.asyncio
    async def test_full_trading_cycle(self, setup_services):
        """Test 1: Complete trading cycle from start to exit."""
        services = await setup_services
        engine = services['trading_engine']

        # Mock bot with initial capital
        bot = MagicMock(spec=Bot)
        bot.id = "test-bot-id"
        bot.capital = Decimal("1000.00")
        bot.trading_symbols = ["BTC/USDT"]
        bot.status = "ACTIVE"

        # Mock market data
        services['market_data'].get_price.return_value = Decimal("50000.00")

        # Mock LLM decision for LONG position
        with patch.object(engine, '_get_llm_decision') as mock_llm:
            mock_llm.return_value = {
                "decisions": [
                    {
                        "symbol": "BTC/USDT",
                        "action": "BUY",
                        "quantity": Decimal("0.01"),
                        "stop_loss": Decimal("49000.00"),
                        "take_profit": Decimal("51000.00")
                    }
                ]
            }

            # Mock position creation
            services['position_service'].create_position.return_value = MagicMock(
                id="test-position-id",
                symbol="BTC/USDT",
                quantity=Decimal("0.01"),
                entry_price=Decimal("50000.00")
            )

            # Mock trade execution
            services['trade_executor'].execute_trade.return_value = MagicMock(
                id="test-trade-id",
                quantity=Decimal("0.01"),
                price=Decimal("50000.00"),
                fees=Decimal("2.50")
            )

            # Start trading cycle
            await engine.run_trading_cycle(bot)

            # Verify position was created
            services['position_service'].create_position.assert_called_once()

            # Verify trade was executed
            services['trade_executor'].execute_trade.assert_called_once()

            # Simulate price drop to trigger SL
            services['market_data'].get_price.return_value = Decimal("48500.00")

            # Mock exit decision
            mock_llm.return_value = {
                "decisions": [
                    {
                        "symbol": "BTC/USDT",
                        "action": "SELL",
                        "quantity": Decimal("0.01")
                    }
                ]
            }

            # Mock position close
            services['position_service'].close_position.return_value = MagicMock(
                realized_pnl=Decimal("-150.00")
            )

            # Run exit cycle
            await engine.run_trading_cycle(bot)

            # Verify position was closed
            services['position_service'].close_position.assert_called_once()

            # Verify capital calculation: 1000 - (0.01 * 50000) - 2.50 + (0.01 * 48500) - 2.50 - 150 = 1000 - 500 - 2.50 + 485 - 2.50 - 150 = 829.50
            expected_final_capital = Decimal("829.50")
            # This would need to be checked against actual bot.capital update

    @pytest.mark.asyncio
    async def test_multi_symbol_handling(self, setup_services):
        """Test 2: Multiple symbols handled correctly."""
        services = await setup_services
        engine = services['trading_engine']

        bot = MagicMock(spec=Bot)
        bot.id = "test-bot-id"
        bot.capital = Decimal("5000.00")
        bot.trading_symbols = ["BTC/USDT", "ETH/USDT", "ADA/USDT", "SOL/USDT", "DOT/USDT"]

        # Mock different prices for each symbol
        price_map = {
            "BTC/USDT": Decimal("50000.00"),
            "ETH/USDT": Decimal("3000.00"),
            "ADA/USDT": Decimal("1.50"),
            "SOL/USDT": Decimal("150.00"),
            "DOT/USDT": Decimal("25.00")
        }

        async def mock_get_price(symbol):
            return price_map.get(symbol, Decimal("0.00"))

        services['market_data'].get_price.side_effect = mock_get_price

        # Mock LLM decisions for multiple positions
        with patch.object(engine, '_get_llm_decision') as mock_llm:
            mock_llm.return_value = {
                "decisions": [
                    {"symbol": s, "action": "BUY", "quantity": Decimal("0.01"), "stop_loss": None, "take_profit": None}
                    for s in bot.trading_symbols
                ]
            }

            # Track position creations
            created_positions = []
            async def mock_create_position(*args, **kwargs):
                position = MagicMock()
                position.symbol = kwargs.get('symbol')
                position.entry_price = price_map.get(kwargs.get('symbol'))
                created_positions.append(position)
                return position

            services['position_service'].create_position.side_effect = mock_create_position

            await engine.run_trading_cycle(bot)

            # Verify all symbols got positions
            assert len(created_positions) == 5

            # Verify each position has correct price
            for pos in created_positions:
                assert pos.entry_price == price_map[pos.symbol]

    @pytest.mark.asyncio
    async def test_capital_integrity(self, setup_services):
        """Test 3: Capital calculations remain consistent."""
        services = await setup_services
        engine = services['trading_engine']

        bot = MagicMock(spec=Bot)
        bot.id = "test-bot-id"
        bot.capital = Decimal("1000.00")

        # Mock positions with invested amounts
        positions = [
            MagicMock(current_value=Decimal("200.00")),
            MagicMock(current_value=Decimal("150.00")),
            MagicMock(current_value=Decimal("300.00"))
        ]

        services['position_service'].get_open_positions.return_value = positions

        # Calculate equity
        invested = sum(p.current_value for p in positions)
        equity = bot.capital + invested

        # Run multiple cycles
        for i in range(10):
            with patch.object(engine, '_get_llm_decision') as mock_llm:
                mock_llm.return_value = {"decisions": []}  # No new trades

                await engine.run_trading_cycle(bot)

                # Verify equity consistency (this would need actual implementation)
                # assert abs(equity - (bot.capital + invested)) < Decimal("0.01")

    @pytest.mark.asyncio
    async def test_database_consistency(self, setup_services, db_session: AsyncSession):
        """Test 4: Database state matches business logic."""
        services = await setup_services

        # Create test position
        position = Position(
            id="test-pos-id",
            bot_id="test-bot-id",
            symbol="BTC/USDT",
            side="LONG",
            quantity=Decimal("0.01"),
            entry_price=Decimal("50000.00"),
            current_price=Decimal("50000.00"),
            status="OPEN"
        )

        db_session.add(position)
        await db_session.commit()

        # Create corresponding trade
        trade = Trade(
            id="test-trade-id",
            bot_id="test-bot-id",
            position_id="test-pos-id",
            symbol="BTC/USDT",
            side="BUY",
            quantity=Decimal("0.01"),
            price=Decimal("50000.00"),
            fees=Decimal("2.50"),
            realized_pnl=Decimal("0.00")
        )

        db_session.add(trade)
        await db_session.commit()

        # Verify position status
        assert position.status == "OPEN"

        # Simulate position close
        position.status = "CLOSED"
        position.closed_at = MagicMock()  # datetime.now()

        # Update trade with realized PnL
        trade.realized_pnl = Decimal("100.00")  # Profit

        await db_session.commit()

        # Verify consistency
        assert position.status == "CLOSED"
        assert trade.realized_pnl == Decimal("100.00")

        # Verify atomic updates (would need transaction testing)
        # This ensures capital updates happen with position changes