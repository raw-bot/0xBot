# Testing Guide for 0xBot Backend

## Overview

This guide documents testing practices and patterns for the 0xBot backend codebase. Our testing strategy focuses on integration and service testing to ensure critical trading functionality works correctly.

## Test Structure

```
backend/tests/
├── conftest.py                 # Shared pytest fixtures and configuration
├── README.md                   # This file
├── services/                   # Service layer unit tests
│   ├── test_market_data_service.py
│   ├── test_market_analysis_service.py
│   ├── test_position_service.py
│   ├── test_risk_manager_service.py
│   ├── test_trade_executor_service.py
│   └── ... (18+ service tests)
├── integration/                # End-to-end workflow tests
│   ├── test_bot_lifecycle.py   # Bot creation, status, equity tracking
│   ├── test_trading_cycle.py   # Complete trading workflows
│   └── test_complete_trading_cycle.py  # Alternative workflow tests
├── routes/                     # API endpoint tests
│   ├── test_auth.py
│   ├── test_bots.py
│   └── test_dashboard.py
└── unit/                       # Isolated unit tests (as needed)
```

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test Categories
```bash
# Integration tests only
pytest tests/integration/ -v

# Service tests only
pytest tests/services/ -v

# Specific test file
pytest tests/services/test_trade_executor_service.py -v

# Specific test class
pytest tests/services/test_market_data_service.py::TestMarketDataService -v

# Specific test
pytest tests/services/test_market_data_service.py::TestMarketDataService::test_fetch_ticker -v
```

### With Coverage
```bash
# Terminal report
pytest --cov=src --cov-report=term-missing -v

# HTML report
pytest --cov=src --cov-report=html -v
# Open htmlcov/index.html in browser
```

### Async Test Debugging
```bash
# Show print statements
pytest tests/ -v -s

# Run with asyncio debug mode
pytest tests/ --asyncio-mode=strict -v
```

## Key Testing Patterns

### 1. Database Fixtures

All database tests use an in-memory SQLite database with automatic rollback:

```python
@pytest.mark.asyncio
async def test_bot_creation(db_session: AsyncSession):
    """Test bot can be created and retrieved."""
    bot = Bot(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="test_bot",
        model_name=ModelName.CLAUDE_SONNET,
        initial_capital=Decimal("50000.00"),
        capital=Decimal("50000.00"),
        trading_symbols=["BTC/USDT"],
        risk_params={},
        status=BotStatus.INACTIVE,
    )
    db_session.add(bot)
    await db_session.commit()

    retrieved = await db_session.get(Bot, bot.id)
    assert retrieved.name == "test_bot"
```

**Key Points**:
- Use `db_session` fixture (async SQLAlchemy session)
- Always `await db_session.commit()` to persist
- Always `await db_session.refresh(obj)` to get updated values
- Session automatically rolls back after test

### 2. Service Testing Pattern

Test services with mocked dependencies:

```python
@pytest.mark.asyncio
async def test_position_opening(db_session: AsyncSession, test_bot: Bot):
    """Test opening a new position."""
    from src.services.position_service import PositionOpen, PositionService

    position_service = PositionService(db=db_session)

    position_data = PositionOpen(
        symbol="BTC/USDT",
        side=PositionSide.LONG.value,
        quantity=Decimal("1.0"),
        entry_price=Decimal("45000"),
        stop_loss=Decimal("43650"),
        take_profit=Decimal("47700"),
    )

    position = await position_service.open_position(test_bot.id, position_data)
    assert position.symbol == "BTC/USDT"
    assert position.status == PositionStatus.OPEN
```

**Key Points**:
- Pass `db=db_session` to services
- Use `PositionOpen` data objects (not dict)
- Always check return values and status

### 3. Mock Exchange Pattern

For tests that need exchange interaction:

```python
async def test_trade_execution(
    db_session: AsyncSession,
    test_bot: Bot,
    mock_exchange,  # From conftest.py
):
    """Test executing a trade with mock exchange."""
    trade_executor = TradeExecutorService(
        db=db_session,
        exchange_client=mock_exchange
    )

    decision = {
        "symbol": "BTC/USDT",
        "side": "long",
        "size_pct": 0.10,
        "entry_price": Decimal("45000"),
        "stop_loss": Decimal("43650"),
        "take_profit": Decimal("47700"),
        "confidence": 0.75,
    }

    position, trade = await trade_executor.execute_entry(
        test_bot, decision, Decimal("45000")
    )
    assert position is not None
```

**Key Points**:
- Mock exchange avoids external API calls
- Pass both `db` and `exchange_client` parameters
- Check both position and trade results

### 4. Integration Test Pattern

Test complete workflows end-to-end:

```python
@pytest.mark.asyncio
async def test_complete_bot_lifecycle(
    db_session: AsyncSession,
    test_bot: Bot,
    test_user: User,
    mock_exchange,
):
    """Test complete bot lifecycle: create → trade → close."""
    # 1. Verify bot created
    assert test_bot.status == BotStatus.INACTIVE

    # 2. Change status
    test_bot.status = BotStatus.ACTIVE
    await db_session.commit()

    # 3. Execute trade
    trade_executor = TradeExecutorService(db=db_session, exchange_client=mock_exchange)
    position, trade = await trade_executor.execute_entry(test_bot, decision, price)
    assert position is not None

    # 4. Close position
    exit_trade = await trade_executor.execute_exit(position, exit_price)
    assert exit_trade is not None

    # 5. Verify final state
    final_position = await position_service.get_position(position.id)
    assert final_position.status == PositionStatus.CLOSED
```

## Common Pitfalls & Solutions

### Issue: `TypeError: PositionService.__init__() got an unexpected keyword argument 'db_session'`

**Solution**: Use `db=` parameter, not `db_session=`:
```python
# ❌ Wrong
position_service = PositionService(db_session=db_session)

# ✅ Correct
position_service = PositionService(db=db_session)
```

### Issue: `AttributeError: 'MarketDataService' object has no attribute 'get_market_snapshot'`

**Solution**: Check the actual method name first:
```bash
grep "def " backend/src/services/market_data_service.py
```

Services often have different method names than expected.

### Issue: `ValueError: invalid UUID 'test-bot-id'`

**Solution**: Always use proper UUIDs in tests, not strings:
```python
# ❌ Wrong
bot.id = "test-bot-id"

# ✅ Correct
bot.id = uuid.uuid4()
```

### Issue: Test passes in isolation but fails in suite

**Solution**: Check for state leaks:
1. Ensure `db_session` rollback works (it should automatically)
2. Don't modify fixtures
3. Use fresh fixtures for each test
4. Check for side effects in services

## Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| Services  | 70%+   | 41%*    |
| API Routes| 80%+   | TBD     |
| Models    | 60%+   | High    |
| Overall   | 80%+   | 41%*    |

*Including only passing tests (integration + services). Some route tests have auth issues.

## Best Practices

1. **Use Fixtures for Common Setup**
   - Test data (bot, user, position, trade)
   - Mocks (exchange, LLM, Redis)
   - Database session

2. **Test Behavior, Not Implementation**
   - Verify side effects (database state)
   - Check return values
   - Don't test internal variable names

3. **Keep Tests Independent**
   - No shared state between tests
   - Each test should be runnable alone
   - Use fresh fixtures

4. **Use Descriptive Names**
   - `test_open_position_with_valid_data` ✅
   - `test_position` ❌

5. **Add Comments for Complex Tests**
   ```python
   async def test_multiple_stops(db_session, test_bot, mock_exchange):
       """Test that both SL and TP can't trigger simultaneously."""
       # Step 1: Create position with SL at 43650, TP at 47700
       # Step 2: Update price to 47500 (between SL and TP)
       # Step 3: Verify only TP triggers (price closer to TP)
   ```

## Debugging Tips

### View Database State During Test
```python
async def test_something(db_session):
    # ... test code ...

    # Debug: print all bots
    result = await db_session.execute(select(Bot))
    bots = result.scalars().all()
    for bot in bots:
        print(f"Bot: {bot.name}, Status: {bot.status}")
```

### Use pytest -s for Prints
```bash
pytest tests/ -s  # Shows all print() outputs
```

### Check What the Mock Returns
```python
async def test_exchange(mock_exchange):
    # See what the mock actually returns
    result = await mock_exchange.fetch_ticker("BTC/USDT")
    print(result)  # Use pytest -s to see output
```

## Contributing New Tests

1. **Choose the Right Category**:
   - Integration test → `tests/integration/`
   - Service test → `tests/services/`
   - API test → `tests/routes/`

2. **Use Existing Fixtures**:
   - Never create `db_session` manually (use fixture)
   - Never create bots manually if `test_bot` fixture works

3. **Follow Naming Convention**:
   - File: `test_<feature>.py`
   - Class: `Test<Feature>`
   - Method: `test_<scenario_and_expected_result>`

4. **Add Docstring**:
   ```python
   async def test_something(fixture):
       """One-line description of what's tested."""
   ```

## Performance

- **Full suite**: ~2 seconds (328 passing tests)
- **Integration tests**: ~1 second (15 tests)
- **Service tests**: ~1 second (238 tests)
- **No tests should exceed 1 second individually**

If a test is slow:
1. Check for unnecessary awaits
2. Reduce database operations
3. Consider moving to unit test
4. Profile with `pytest --durations=10`

## CI/CD

Tests automatically run on:
- Every push to `master`, `main`, `develop`
- Every pull request

Workflow runs in GitHub Actions with:
- Python 3.13
- PostgreSQL 16
- Coverage reporting to Codecov
- Minimum 50% coverage enforcement

See `.github/workflows/test.yml` for details.
