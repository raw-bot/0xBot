"""
Pytest configuration and fixtures for 0xBot testing.

Provides reusable fixtures for database, async sessions, test data, and mocked services.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.core.database import Base
from src.models.bot import Bot, BotStatus, ModelName
from src.models.user import User
from src.models.position import Position, PositionStatus, PositionSide
from src.models.trade import Trade, TradeSide
from src.models.equity_snapshot import EquitySnapshot
from src.models.llm_decision import LLMDecision


# ==============================================================================
# DATABASE FIXTURES
# ==============================================================================


@pytest_asyncio.fixture
async def test_db_engine():
    """Create in-memory SQLite database engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for testing."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    async_session = async_sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


# ==============================================================================
# TEST DATA FIXTURES
# ==============================================================================


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash="hashed_password_123",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def test_bot(db_session: AsyncSession, test_user: User) -> Bot:
    """Create a test bot with default settings."""
    bot = Bot(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="test_bot",
        model_name=ModelName.CLAUDE_SONNET,
        initial_capital=Decimal("10000.00"),
        capital=Decimal("10000.00"),
        trading_symbols=["BTC/USDT", "ETH/USDT"],
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
    db_session.add(bot)
    await db_session.commit()
    return bot


@pytest_asyncio.fixture
async def test_position(db_session: AsyncSession, test_bot: Bot) -> Position:
    """Create a test open position."""
    position = Position(
        id=uuid.uuid4(),
        bot_id=test_bot.id,
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        quantity=Decimal("1.0"),
        entry_price=Decimal("45000.00"),
        current_price=Decimal("46000.00"),
        status=PositionStatus.OPEN,
        stop_loss=Decimal("43650.00"),  # -3%
        take_profit=Decimal("47700.00"),  # +6%
        opened_at=datetime.utcnow(),
    )
    db_session.add(position)
    await db_session.commit()
    return position


@pytest_asyncio.fixture
async def test_trade(db_session: AsyncSession, test_bot: Bot) -> Trade:
    """Create a test completed trade."""
    trade = Trade(
        id=uuid.uuid4(),
        bot_id=test_bot.id,
        symbol="BTC/USDT",
        side=TradeSide.BUY,
        quantity=Decimal("1.0"),
        price=Decimal("45000.00"),
        fees=Decimal("10.00"),
        realized_pnl=Decimal("1490.00"),  # (46500 - 45000) * 1 - 10
        executed_at=datetime.utcnow(),
    )
    db_session.add(trade)
    await db_session.commit()
    return trade


@pytest_asyncio.fixture
async def test_equity_snapshot(db_session: AsyncSession, test_bot: Bot) -> EquitySnapshot:
    """Create a test equity snapshot."""
    snapshot = EquitySnapshot(
        id=uuid.uuid4(),
        bot_id=test_bot.id,
        total_value=Decimal("10500.00"),
        cash=Decimal("9000.00"),
        positions_value=Decimal("1500.00"),
        unrealized_pnl=Decimal("500.00"),
        realized_pnl=Decimal("0.00"),
        timestamp=datetime.utcnow(),
    )
    db_session.add(snapshot)
    await db_session.commit()
    return snapshot


# ==============================================================================
# MOCK FIXTURES
# ==============================================================================


@pytest.fixture
def mock_exchange():
    """Create a mocked exchange client."""
    exchange = AsyncMock()
    exchange.fetch_ohlcv = AsyncMock(
        return_value=[
            [1000000, 45000, 46000, 44500, 45500, 100],  # [timestamp, o, h, l, c, v]
            [1001000, 45500, 46500, 45000, 46000, 120],
        ]
    )
    exchange.create_order = AsyncMock(return_value={"id": "order_123", "status": "closed"})
    exchange.cancel_order = AsyncMock(return_value={"id": "order_123", "status": "canceled"})
    exchange.fetch_balance = AsyncMock(
        return_value={
            "BTC": {"free": 1.0, "used": 0.0, "total": 1.0},
            "USDT": {"free": 5000.0, "used": 0.0, "total": 5000.0},
            "free": 5000.0,
            "used": 0.0,
            "total": 10000.0,
        }
    )
    return exchange


@pytest.fixture
def mock_llm_client():
    """Create a mocked LLM client."""
    llm = AsyncMock()
    llm.messages.create = AsyncMock(
        return_value=MagicMock(
            content=[MagicMock(text='{"action": "HOLD", "confidence": 0.7}')]
        )
    )
    return llm


@pytest.fixture
def mock_redis_client():
    """Create a mocked Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.incr = AsyncMock(return_value=1)
    redis.delete = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    return redis


# ==============================================================================
# TEST CONSTANTS
# ==============================================================================


class TestConstants:
    """Test configuration constants."""

    # User constants
    TEST_EMAIL = "test@example.com"
    TEST_PASSWORD = "test_password_123"
    TEST_PASSWORD_HASH = "hashed_password_123"

    # Bot constants
    TEST_BOT_NAME = "test_bot"
    TEST_INITIAL_CAPITAL = Decimal("10000.00")
    TEST_TRADING_SYMBOLS = ["BTC/USDT", "ETH/USDT"]
    TEST_MODEL_NAME = ModelName.CLAUDE_SONNET

    # Position constants
    TEST_SYMBOL = "BTC/USDT"
    TEST_ENTRY_PRICE = Decimal("45000.00")
    TEST_CURRENT_PRICE = Decimal("46000.00")
    TEST_QUANTITY = Decimal("1.0")
    TEST_STOP_LOSS = Decimal("43650.00")
    TEST_TAKE_PROFIT = Decimal("47700.00")

    # Risk parameters
    DEFAULT_RISK_PARAMS = {
        "max_position_pct": 0.10,
        "max_drawdown_pct": 0.20,
        "max_trades_per_day": 10,
        "stop_loss_pct": 0.03,
        "take_profit_pct": 0.06,
    }


@pytest.fixture
def test_constants():
    """Provide test constants."""
    return TestConstants


# ==============================================================================
# PYTEST CONFIGURATION
# ==============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
