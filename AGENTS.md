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

**Framework**: pytest with asyncio support

**Pattern**:
```python
@pytest.mark.asyncio
async def test_something():
    # Test code
```

**What Works**:
- (To be discovered during audit)

**Gotchas**:
- (To be discovered during audit)

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

**Caching**:
- Redis available
- Usage: (To be discovered during audit)

**Async Patterns**:
- FastAPI: Full async/await
- Database: asyncpg for PostgreSQL
- Exchange API: async CCXT wrapper

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

**Last Updated**: 2026-01-18
**Updated By**: Initial Setup
**Next Update**: After Audit Task 1 completion
