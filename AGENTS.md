# AGENTS.md - Discovered Patterns & Knowledge Base

This document captures reusable patterns, gotchas, and useful context discovered during development and auditing iterations. Future AI agents working on this codebase should read this first.

---

## Architecture Patterns

### Block-Based Pipeline (Trading Decision)
**Context**: 0xBot uses a block orchestrator pattern for trading decisions.

**Pattern**:
```
MarketDataBlock → PortfolioBlock → DecisionBlock → RiskBlock → ExecutionBlock
```

**What Works**:
- Clear separation of concerns
- Easy to swap decision strategies (LLM, Trinity, Indicator)
- Testable in isolation

**Gotchas**:
- (To be discovered during audit)

**Files**: `backend/src/blocks/`, `backend/src/core/scheduler.py`

---

## Code Quality Patterns

### Type Hints & MyPy
**Context**: Project uses Python 3.11+ with strict mypy checking.

**Pattern**: All functions must have complete type hints:
```python
async def process_data(data: dict[str, Any]) -> Optional[Trade]:
    """Process market data and return trade if signaled."""
```

**What Works**:
- Catches bugs early
- Self-documenting code

**Gotchas**:
- (To be discovered during audit)

---

## Testing Patterns

**Framework**: pytest with asyncio support (3.13+ compatible)

**Service Initialization** (Critical!):
```python
# ❌ WRONG - incorrect parameter names
position_service = PositionService(db_session=db_session)
trade_executor = TradeExecutorService(exchange=mock_exchange, db_session=db_session)
market_data = MarketDataService(exchange=mock_exchange)

# ✅ CORRECT - use actual parameter names
position_service = PositionService(db=db_session)
trade_executor = TradeExecutorService(db=db_session, exchange_client=mock_exchange)
market_data = MarketDataService(exchange_client=mock_exchange)
```

**Position Service Data Pattern**:
```python
# ❌ WRONG - passing dict to open_position
position_data = {
    "symbol": "BTC/USDT",
    "side": "long",
    ...
}
position = await position_service.open_position(position_data)

# ✅ CORRECT - use PositionOpen data class
from src.services.position_service import PositionOpen
position_data = PositionOpen(
    symbol="BTC/USDT",
    side=PositionSide.LONG.value,
    ...
)
position = await position_service.open_position(test_bot.id, position_data)
```

**TradeExecutorService.execute_exit Return Type**:
```python
# ❌ WRONG - expects tuple
exit_position, exit_trade = await trade_executor.execute_exit(test_bot, position_id, exit_price)

# ✅ CORRECT - returns Optional[Trade] or None
exit_trade = await trade_executor.execute_exit(position, exit_price)
```

**Risk Validation Signature**:
```python
# ❌ WRONG - missing parameters
is_valid, error = risk_manager.validate_entry(test_bot, decision)

# ✅ CORRECT - includes current_positions and current_price
is_valid, error = risk_manager.validate_entry(
    test_bot, decision, current_positions=[], current_price=Decimal("47000")
)
```

**What Works**:
- Async/await with pytest-asyncio properly handles database sessions
- Automatic rollback after each test prevents state leaks
- Fixture pattern with in-memory SQLite for fast integration tests
- Mock exchange pattern avoids external API dependency
- 328 tests pass consistently with 0 flaky tests

**Gotchas**:
- BotStatus enum: INACTIVE, ACTIVE, PAUSED, STOPPED (NOT RUNNING)
- EquitySnapshot field is `equity` not `total_value`
- Position doesn't have `exit_price` field (use `closed_at` to verify closure)
- check_stop_loss_take_profit returns Optional[str] ("stop_loss", "take_profit", or None)
- get_all_positions returns tuple (list, total_count) not just list
- Service method names may differ from expectations - always check actual implementation
- Capital calculations are complex with fees and margin - avoid asserting exact amounts
- Mock exchange complexity should be minimized - simplified tests are more reliable

---

## Security Patterns

**JWT Authentication**:
- Located in: `backend/src/middleware/auth.py`
- Token validation for protected routes
- WebSocket auth not yet implemented (audit item)

**Pattern to Follow**:
- Always validate tokens before accessing user data
- Extract user_id from JWT claims
- Verify user owns the resource

**Gotchas**:
- (To be discovered during audit)

---

## Database Patterns

**ORM**: SQLAlchemy 2.0+ async

**Pattern**:
```python
class BotModel(Base):
    __tablename__ = "bots"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
```

**Relationships**:
```python
user: Mapped["UserModel"] = relationship(back_populates="bots")
positions: Mapped[list["PositionModel"]] = relationship()
```

**What Works**:
- (To be discovered during audit)

**Gotchas**:
- (To be discovered during audit)

---

## Common File Locations

| Purpose | Location |
|---------|----------|
| FastAPI app entry | `backend/src/main.py` |
| Database models | `backend/src/models/` |
| Business logic | `backend/src/services/` |
| Trading pipeline | `backend/src/blocks/` |
| Infrastructure | `backend/src/core/` |
| API endpoints | `backend/src/routes/` |
| Frontend components | `frontend/src/components/` |
| Frontend pages | `frontend/src/pages/` |

---

## Configuration & Environment

**Key Environment Variables**:
- `JWT_SECRET`: JWT signing key (CRITICAL - no default)
- `OKX_API_KEY`: Exchange API key
- `DATABASE_URL`: PostgreSQL connection
- `REDIS_URL`: Redis connection

**Pattern**: All sensitive values should use environment variables, never hardcoded.

---

## Deployment & DevOps

**Infrastructure**:
- Docker Compose for local development
- PostgreSQL 15 + Redis 7
- FastAPI on Uvicorn (port 8020)
- Vite dev server (port 5173)

**What Works**:
- (To be discovered during audit)

**Gotchas**:
- (To be discovered during audit)

---

## Performance Optimizations

**Database Connections**:
- Current: NullPool (new connection per request)
- Should be: QueuePool for production

**Caching Pattern**:
- Redis caching service implemented in `backend/src/services/cache_service.py`
- CacheService provides generic cache operations with TTL support
- Market data caching: OHLCV (5m), ticker (5m), funding rates (5m), open interest (5m)
- Usage pattern: Services receive optional `cache_service` parameter
- All cache methods are async: `get_cached(key)`, `set_cached(key, value, ttl)`
- Cache hits/misses tracked automatically with `get_hit_rate()` and `get_cache_stats()`
- Pattern invalidation with `invalidate_pattern(pattern)` for bulk invalidation
- Graceful degradation: services work with or without cache (check if `self.cache` is not None)
- JSON serialization handles complex types (Decimal, datetime) with `default=str`

**Async Patterns**:
- FastAPI: Full async/await
- Database: asyncpg for PostgreSQL
- Exchange API: async CCXT wrapper
- Redis: async redis-py with connection pooling

---

## Troubleshooting Guide

### API Won't Start
- Check JWT_SECRET environment variable is set
- Check database connection string
- Check Redis availability

### Tests Failing
- Ensure pytest-asyncio installed
- Check database migrations ran
- Review test fixtures

(More to be added as issues discovered)

---

## Next Agent's Checklist

When starting work on 0xBot:
- [ ] Read this file first
- [ ] Review AUDIT_REPORT.md for current issues
- [ ] Check progress.txt for recent learnings
- [ ] Run `pytest --cov` to understand coverage gaps
- [ ] Run `mypy src --strict` to see type check issues
- [ ] Review git log to see recent patterns

---

**Last Updated**: 2026-01-19
**Updated By**: Ralph (Caching Implementation, Task 7)
**Last Changes**:
- Implemented Redis caching strategy for market data (5-minute TTL)
- Created CacheService with generic cache operations, metrics tracking, pattern invalidation
- Integrated caching into MarketDataService (OHLCV, ticker, funding rates, open interest)
- Added comprehensive test suite: 39 tests for cache_service (100% passing)
- All tests passing: 81/81 (cache + market_data services)
- Documented caching patterns for future development
- Backward compatible implementation with graceful degradation

**Next Steps**:
- Task 8: Cache Technical Indicators (15-minute TTL) - indicators service integration
- Task 9: Verify Performance Improvements - benchmarking before/after metrics
- Task 10: Create Performance Documentation - PERFORMANCE.md guide
