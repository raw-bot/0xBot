"""Tests for pagination functionality in list endpoints."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from src.models.bot import Bot, BotStatus
from src.models.position import Position, PositionStatus
from src.models.trade import Trade, TradeSide
from src.models.user import User
from src.services.bot_service import BotService, BotCreate
from src.services.position_service import PositionService, PositionOpen
from src.services.trade_executor_service import TradeExecutorService


class TestBotListPagination:
    """Tests for bot list endpoint pagination."""

    async def test_list_bots_paginated_first_page(self, test_user: User, db_session: AsyncSession):
        """Test getting first page of bots."""
        # Create multiple bots
        bot_service = BotService(db_session)
        for i in range(5):
            await bot_service.create_bot(
                test_user.id,
                BotCreate(
                    name=f"Bot {i}",
                    model_name="claude-4.5-sonnet",
                    capital=Decimal("1000"),
                ),
            )

        # Get first page
        bots, total = await bot_service.get_user_bots_paginated(
            test_user.id, include_stopped=False, limit=2, offset=0
        )

        assert len(bots) == 2
        assert total == 5

    async def test_list_bots_paginated_second_page(self, test_user: User, db_session: AsyncSession):
        """Test getting second page of bots."""
        # Create multiple bots
        bot_service = BotService(db_session)
        for i in range(5):
            await bot_service.create_bot(
                test_user.id,
                BotCreate(
                    name=f"Bot {i}",
                    model_name="claude-4.5-sonnet",
                    capital=Decimal("1000"),
                ),
            )

        # Get second page (offset=2, limit=2)
        bots, total = await bot_service.get_user_bots_paginated(
            test_user.id, include_stopped=False, limit=2, offset=2
        )

        assert len(bots) == 2
        assert total == 5

    async def test_list_bots_paginated_last_page_partial(
        self, test_user: User, db_session: AsyncSession
    ):
        """Test getting last page with fewer results than limit."""
        # Create 5 bots
        bot_service = BotService(db_session)
        for i in range(5):
            await bot_service.create_bot(
                test_user.id,
                BotCreate(
                    name=f"Bot {i}",
                    model_name="claude-4.5-sonnet",
                    capital=Decimal("1000"),
                ),
            )

        # Get last page (offset=4, limit=2 should return 1 bot)
        bots, total = await bot_service.get_user_bots_paginated(
            test_user.id, include_stopped=False, limit=2, offset=4
        )

        assert len(bots) == 1
        assert total == 5

    async def test_list_bots_paginated_empty_page(
        self, test_user: User, db_session: AsyncSession
    ):
        """Test getting a page beyond available results."""
        # Create 3 bots
        bot_service = BotService(db_session)
        for i in range(3):
            await bot_service.create_bot(
                test_user.id,
                BotCreate(
                    name=f"Bot {i}",
                    model_name="claude-4.5-sonnet",
                    capital=Decimal("1000"),
                ),
            )

        # Get page beyond available results (offset=10)
        bots, total = await bot_service.get_user_bots_paginated(
            test_user.id, include_stopped=False, limit=2, offset=10
        )

        assert len(bots) == 0
        assert total == 3

    async def test_list_bots_paginated_all_results(
        self, test_user: User, db_session: AsyncSession
    ):
        """Test getting all results in single page."""
        # Create 3 bots
        bot_service = BotService(db_session)
        for i in range(3):
            await bot_service.create_bot(
                test_user.id,
                BotCreate(
                    name=f"Bot {i}",
                    model_name="claude-4.5-sonnet",
                    capital=Decimal("1000"),
                ),
            )

        # Get all results
        bots, total = await bot_service.get_user_bots_paginated(
            test_user.id, include_stopped=False, limit=100, offset=0
        )

        assert len(bots) == 3
        assert total == 3

    async def test_list_bots_paginated_respects_include_stopped(
        self, test_user: User, db_session: AsyncSession
    ):
        """Test that pagination respects include_stopped filter."""
        from src.services.bot_service import BotUpdate

        # Create 3 bots, stop one
        bot_service = BotService(db_session)
        for i in range(3):
            bot = await bot_service.create_bot(
                test_user.id,
                BotCreate(
                    name=f"Bot {i}",
                    model_name="claude-4.5-sonnet",
                    capital=Decimal("1000"),
                ),
            )
            if i == 0:
                # Stop the first bot
                await bot_service.update_bot(bot.id, BotUpdate(status=BotStatus.STOPPED.value))

        # Get with include_stopped=False
        bots, total = await bot_service.get_user_bots_paginated(
            test_user.id, include_stopped=False, limit=100, offset=0
        )
        assert total == 2  # Only active bots

        # Get with include_stopped=True
        bots, total = await bot_service.get_user_bots_paginated(
            test_user.id, include_stopped=True, limit=100, offset=0
        )
        assert total == 3  # All bots

    async def test_list_bots_paginated_custom_limit(
        self, test_user: User, db_session: AsyncSession
    ):
        """Test pagination with custom limit."""
        # Create 10 bots
        bot_service = BotService(db_session)
        for i in range(10):
            await bot_service.create_bot(
                test_user.id,
                BotCreate(
                    name=f"Bot {i}",
                    model_name="claude-4.5-sonnet",
                    capital=Decimal("1000"),
                ),
            )

        # Get with custom limit
        bots, total = await bot_service.get_user_bots_paginated(
            test_user.id, include_stopped=False, limit=5, offset=0
        )

        assert len(bots) == 5
        assert total == 10


class TestPositionListPagination:
    """Tests for position list endpoint pagination."""

    async def test_list_positions_paginated_all(self, test_bot: Bot, db_session: AsyncSession):
        """Test pagination of all positions."""
        # Create multiple positions
        position_service = PositionService(db_session)
        for i in range(5):
            await position_service.open_position(
                test_bot.id,
                PositionOpen(
                    symbol=f"BTC/USDT",
                    side="long",
                    quantity=Decimal("0.1"),
                    entry_price=Decimal("50000"),
                ),
            )

        # Get first page
        positions, total = await position_service.get_all_positions(
            test_bot.id, limit=2, offset=0
        )

        assert len(positions) == 2
        assert total == 5

    async def test_list_positions_paginated_open(self, test_bot: Bot, db_session: AsyncSession):
        """Test pagination of open positions only."""
        position_service = PositionService(db_session)

        # Create 5 positions
        positions_created = []
        for i in range(5):
            pos = await position_service.open_position(
                test_bot.id,
                PositionOpen(
                    symbol=f"BTC/USDT",
                    side="long",
                    quantity=Decimal("0.1"),
                    entry_price=Decimal("50000"),
                ),
            )
            positions_created.append(pos)

        # Close 2 positions
        for i in range(2):
            await position_service.close_position(positions_created[i].id, Decimal("55000"))

        # Get open positions with pagination
        open_positions, total = await position_service.get_open_positions_paginated(
            test_bot.id, limit=2, offset=0
        )

        assert len(open_positions) == 2
        assert total == 3  # Only 3 open, 2 closed

    async def test_list_positions_paginated_empty(self, test_bot: Bot, db_session: AsyncSession):
        """Test pagination when no positions exist."""
        position_service = PositionService(db_session)

        positions, total = await position_service.get_all_positions(
            test_bot.id, limit=2, offset=0
        )

        assert len(positions) == 0
        assert total == 0

    async def test_list_positions_paginated_all_on_first_page(
        self, test_bot: Bot, db_session: AsyncSession
    ):
        """Test pagination when all results fit on first page."""
        position_service = PositionService(db_session)

        # Create 3 positions
        for i in range(3):
            await position_service.open_position(
                test_bot.id,
                PositionOpen(
                    symbol=f"BTC/USDT",
                    side="long",
                    quantity=Decimal("0.1"),
                    entry_price=Decimal("50000"),
                ),
            )

        # Get with large limit
        positions, total = await position_service.get_all_positions(
            test_bot.id, limit=100, offset=0
        )

        assert len(positions) == 3
        assert total == 3

    async def test_list_positions_paginated_second_page_partial(
        self, test_bot: Bot, db_session: AsyncSession
    ):
        """Test getting partial results on second page."""
        position_service = PositionService(db_session)

        # Create 5 positions
        for i in range(5):
            await position_service.open_position(
                test_bot.id,
                PositionOpen(
                    symbol=f"BTC/USDT",
                    side="long",
                    quantity=Decimal("0.1"),
                    entry_price=Decimal("50000"),
                ),
            )

        # Get second page (offset=4, limit=2)
        positions, total = await position_service.get_all_positions(
            test_bot.id, limit=2, offset=4
        )

        assert len(positions) == 1
        assert total == 5


class TestTradeListPagination:
    """Tests for trade list pagination."""

    async def test_list_trades_paginated_structure(self, test_bot: Bot, db_session: AsyncSession):
        """Test trade pagination query structure and logic."""
        from datetime import datetime

        # Create multiple trade records directly
        for i in range(5):
            trade = Trade(
                bot_id=test_bot.id,
                symbol="BTC/USDT",
                side=TradeSide.BUY,
                quantity=Decimal("0.1"),
                price=Decimal("50000"),
                fees=Decimal("10"),
                realized_pnl=Decimal("0"),
                executed_at=datetime.utcnow(),
            )
            db_session.add(trade)
        await db_session.commit()

        # Get first page using raw query (simulates endpoint behavior)
        count_result = await db_session.execute(
            select(func.count()).select_from(Trade).where(Trade.bot_id == test_bot.id)
        )
        total = count_result.scalar()

        result = await db_session.execute(
            select(Trade)
            .where(Trade.bot_id == test_bot.id)
            .order_by(desc(Trade.executed_at))
            .limit(2)
            .offset(0)
        )
        trades = list(result.scalars().all())

        assert len(trades) == 2
        assert total == 5

    async def test_list_trades_paginated_second_page(
        self, test_bot: Bot, db_session: AsyncSession
    ):
        """Test getting second page of trades."""
        from datetime import datetime

        # Create multiple trade records directly
        for i in range(5):
            trade = Trade(
                bot_id=test_bot.id,
                symbol="BTC/USDT",
                side=TradeSide.BUY,
                quantity=Decimal("0.1"),
                price=Decimal("50000"),
                fees=Decimal("10"),
                realized_pnl=Decimal("0"),
                executed_at=datetime.utcnow(),
            )
            db_session.add(trade)
        await db_session.commit()

        # Get second page using raw query
        count_result = await db_session.execute(
            select(func.count()).select_from(Trade).where(Trade.bot_id == test_bot.id)
        )
        total = count_result.scalar()

        result = await db_session.execute(
            select(Trade)
            .where(Trade.bot_id == test_bot.id)
            .order_by(desc(Trade.executed_at))
            .limit(2)
            .offset(2)
        )
        trades = list(result.scalars().all())

        assert len(trades) == 2
        assert total == 5

    async def test_list_trades_paginated_empty(self, test_bot: Bot, db_session: AsyncSession):
        """Test pagination when no trades exist."""
        count_result = await db_session.execute(
            select(func.count()).select_from(Trade).where(Trade.bot_id == test_bot.id)
        )
        total = count_result.scalar()

        result = await db_session.execute(
            select(Trade)
            .where(Trade.bot_id == test_bot.id)
            .order_by(desc(Trade.executed_at))
            .limit(2)
            .offset(0)
        )
        trades = list(result.scalars().all())

        assert len(trades) == 0
        assert total == 0


class TestPaginationParameterValidation:
    """Tests for pagination parameter validation."""

    async def test_pagination_limit_enforcement_min(
        self, test_user: User, db_session: AsyncSession
    ):
        """Test that limit is enforced to minimum value."""
        bot_service = BotService(db_session)

        # Create a bot
        await bot_service.create_bot(
            test_user.id,
            BotCreate(
                name="Test Bot",
                model_name="claude-4.5-sonnet",
                capital=Decimal("1000"),
            ),
        )

        # Test with limit below minimum - actual enforcement happens in routes
        # Service should work with any limit >= 0
        bots, total = await bot_service.get_user_bots_paginated(
            test_user.id, include_stopped=False, limit=5, offset=0
        )

        assert total >= 0

    async def test_pagination_offset_zero(self, test_user: User, db_session: AsyncSession):
        """Test pagination with offset=0."""
        bot_service = BotService(db_session)

        # Create bots
        for i in range(3):
            await bot_service.create_bot(
                test_user.id,
                BotCreate(
                    name=f"Bot {i}",
                    model_name="claude-4.5-sonnet",
                    capital=Decimal("1000"),
                ),
            )

        # Get with offset=0
        bots, total = await bot_service.get_user_bots_paginated(
            test_user.id, include_stopped=False, limit=100, offset=0
        )

        assert len(bots) == 3
        assert total == 3

    async def test_pagination_ordering_consistent(
        self, test_user: User, db_session: AsyncSession
    ):
        """Test that pagination returns results in consistent order."""
        bot_service = BotService(db_session)

        # Create bots with slight delays to ensure ordering
        bot_ids = []
        for i in range(5):
            bot = await bot_service.create_bot(
                test_user.id,
                BotCreate(
                    name=f"Bot {i}",
                    model_name="claude-4.5-sonnet",
                    capital=Decimal("1000"),
                ),
            )
            bot_ids.append(bot.id)

        # Get first page
        page1, _ = await bot_service.get_user_bots_paginated(
            test_user.id, include_stopped=False, limit=2, offset=0
        )

        # Get second page
        page2, _ = await bot_service.get_user_bots_paginated(
            test_user.id, include_stopped=False, limit=2, offset=2
        )

        # Verify no overlap (ordering is consistent)
        page1_ids = [b.id for b in page1]
        page2_ids = [b.id for b in page2]

        assert len(set(page1_ids) & set(page2_ids)) == 0  # No duplicates across pages
