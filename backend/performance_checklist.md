# Performance Optimization Checklist

Use this checklist when adding new features, endpoints, or services to ensure performance standards are met.

## Pre-Development

- [ ] Read PERFORMANCE.md (connection pooling, query optimization, caching patterns)
- [ ] Review existing query patterns in `src/services/` and `src/routes/`
- [ ] Understand target performance: <50ms for queries, <100ms for dashboard endpoints
- [ ] Plan caching strategy if appropriate (market data, indicators, expensive calculations)

## During Development

### Endpoint Development

- [ ] **Database Queries**
  - [ ] Use selectinload for all related objects (no N+1 queries)
  - [ ] Add pagination with default limit=100, max limit=1000
  - [ ] Test query count with SQL logging enabled
  - [ ] Verify no full table scans (use WHERE clauses with indices)
  - [ ] Use appropriate indices on filtered columns

- [ ] **Caching**
  - [ ] Identify expensive operations (API calls, calculations, complex queries)
  - [ ] Add cache layer with appropriate TTL:
    - [ ] Market data: 5-minute TTL
    - [ ] Indicators: 15-minute TTL
    - [ ] User-specific data: 1-hour TTL
  - [ ] Implement cache invalidation (TTL-based or event-based)
  - [ ] Log cache hits/misses for monitoring

- [ ] **Async Operations**
  - [ ] Use asyncio.gather() for concurrent operations (API calls, queries)
  - [ ] Avoid sequential operations where parallelization is possible
  - [ ] Set appropriate timeouts (30 seconds for API calls, 5 seconds for DB)
  - [ ] Handle timeouts gracefully (retry with backoff or return cached value)

- [ ] **Error Handling**
  - [ ] Catch specific exceptions (not generic `Exception`)
  - [ ] Log errors with context (operation name, parameters, error details)
  - [ ] Implement graceful degradation (use cached value on error)
  - [ ] Avoid cascading failures (circuit breaker pattern)

### Service Development

- [ ] **Constructor**
  - [ ] Accept optional `cache_service` parameter for caching support
  - [ ] Allow graceful operation without cache (cache_service=None)
  - [ ] Initialize any required connections

- [ ] **Methods**
  - [ ] Use type hints for all parameters and return values
  - [ ] Add docstrings with performance characteristics
  - [ ] Use `await` properly for async operations
  - [ ] Return early on errors (don't process partial data)

- [ ] **Logging**
  - [ ] Log operation start/end with timestamps
  - [ ] Log query count and execution time
  - [ ] Log cache hits/misses
  - [ ] Include context (user_id, bot_id, symbol, etc.)

## Pre-Testing

### Query Testing

- [ ] Create test with realistic data volume:
  - [ ] 50+ positions
  - [ ] 500+ trades
  - [ ] 100+ bots
  - [ ] Multiple time periods (1h, 4h, 1d)

- [ ] Verify no N+1 queries:
  ```bash
  # Run with SQL logging
  SQLALCHEMY_ECHO=true pytest your_test.py -v
  # Count queries - should match expected count
  ```

- [ ] Benchmark query execution:
  ```python
  import time
  start = time.time()
  result = await operation()
  elapsed = (time.time() - start) * 1000
  assert elapsed < 50, f"Query took {elapsed}ms (target <50ms)"
  ```

### Cache Testing

- [ ] Verify cache storage:
  - [ ] Check Redis keys exist: `redis-cli keys cache:*`
  - [ ] Verify TTL values: `redis-cli ttl cache:market:*`
  - [ ] Check metrics: `redis-cli get metrics:cache_hits:*`

- [ ] Test cache invalidation:
  - [ ] First call: cache miss, slow operation
  - [ ] Second call: cache hit, fast operation
  - [ ] After TTL: cache miss again
  - [ ] After manual invalidation: cache miss

### Pagination Testing

- [ ] Default pagination works:
  ```python
  response = client.get("/api/trades")  # Returns first 100
  assert len(response["data"]) == 100
  assert response["pagination"]["page"] == 1
  ```

- [ ] Custom limit works:
  ```python
  response = client.get("/api/trades?limit=50")
  assert len(response["data"]) == 50
  assert response["pagination"]["limit"] == 50
  ```

- [ ] Max limit enforced:
  ```python
  response = client.get("/api/trades?limit=5000")
  assert response["pagination"]["limit"] == 1000  # Capped at max
  ```

- [ ] Pagination metadata correct:
  ```python
  assert "total" in response["pagination"]
  assert "pages" in response["pagination"]
  expected_pages = (total + limit - 1) // limit
  assert response["pagination"]["pages"] == expected_pages
  ```

## Testing & Benchmarking

### Run Performance Tests

```bash
# All performance tests
pytest backend/tests/performance/ -v

# Specific category
pytest backend/tests/performance/test_query_performance.py -v
pytest backend/tests/performance/test_dashboard_performance.py -v
pytest backend/tests/performance/test_connection_pooling.py -v
pytest backend/tests/performance/test_concurrent_bots.py -v

# With profiling
python -m cProfile -s cumulative -m pytest backend/tests/performance/
```

### Performance Targets

| Operation | Target | Acceptable | Unacceptable |
|---|---|---|---|
| Single query | <10ms | <50ms | >100ms |
| Dashboard endpoint | <50ms | <100ms | >200ms |
| Concurrent 10 bots | <50ms queries | <100ms endpoint | >200ms |
| Cache operation | <10ms | <20ms | >50ms |
| Pagination (1000 items) | <20ms | <50ms | >100ms |

## Pre-Deployment

### Code Review Checklist

- [ ] **Queries**
  - [ ] No N+1 queries (verified with SQL logging)
  - [ ] Uses selectinload for related objects
  - [ ] Pagination applied with limits
  - [ ] Query count < 5 for single logical operation
  - [ ] Execution time < 50ms with realistic data

- [ ] **Caching**
  - [ ] Caching layer implemented for expensive operations
  - [ ] TTL values appropriate (5min/15min/1hour)
  - [ ] Cache invalidation strategy documented
  - [ ] Cache keys follow naming convention
  - [ ] Fallback works when cache unavailable

- [ ] **Async/Concurrency**
  - [ ] All I/O operations use `await`
  - [ ] Concurrent operations use `asyncio.gather()`
  - [ ] Timeouts configured and handled
  - [ ] No blocking calls in async context

- [ ] **Error Handling**
  - [ ] Specific exceptions caught (not generic `Exception`)
  - [ ] Errors logged with full context
  - [ ] Graceful degradation implemented
  - [ ] No cascading failures

- [ ] **Documentation**
  - [ ] Docstrings include performance characteristics
  - [ ] Complex logic documented with comments
  - [ ] Cache strategy documented
  - [ ] Known limitations noted

- [ ] **Tests**
  - [ ] Unit tests cover happy path and edge cases
  - [ ] Integration tests verify end-to-end performance
  - [ ] Performance tests assert latency targets
  - [ ] Tests pass locally (no flaky tests)

### Monitoring Setup

- [ ] **Logging Configured**
  - [ ] Query performance logged
  - [ ] Cache hits/misses tracked
  - [ ] Error rates monitored
  - [ ] Resource usage tracked

- [ ] **Metrics Collection**
  - [ ] Query latency percentiles (p50, p95, p99)
  - [ ] Cache hit rate tracked
  - [ ] Error rate tracked
  - [ ] Pool utilization monitored

- [ ] **Alerts Configured**
  - [ ] Alert on slow queries (>100ms)
  - [ ] Alert on high error rate (>5%)
  - [ ] Alert on connection pool exhaustion
  - [ ] Alert on cache failure

## Post-Deployment

### Day 1 Monitoring

- [ ] Error rates normal (< 1%)
- [ ] Query latency acceptable (p95 < 100ms)
- [ ] Cache hit rate > 70% for cached operations
- [ ] No connection pool exhaustion errors
- [ ] Resource usage (CPU, memory, connections) within limits

### Week 1 Analysis

- [ ] Actual vs. expected performance metrics
- [ ] Identify any new bottlenecks
- [ ] Collect data for optimization opportunities
- [ ] Update documentation with real-world results

### Ongoing Maintenance

- [ ] Monthly performance review
- [ ] Update PERFORMANCE.md with new patterns
- [ ] Profile and optimize slow endpoints
- [ ] Remove unused caches
- [ ] Expand caching for new expensive operations

## Quick Reference

### Common Patterns

```python
# ✅ Query with eager loading
bot = await db.query(Bot).options(
    selectinload(Bot.positions)
    .selectinload(Position.equity_snapshots)
).filter(Bot.id == bot_id).first()

# ✅ Paginated query
trades = await db.query(Trade)\
    .offset((page - 1) * limit)\
    .limit(limit)\
    .all()

# ✅ Cached operation
value = await cache_service.get_cached(
    key="my_key",
    fetch_fn=expensive_operation,
    ttl=300
)

# ✅ Concurrent operations
results = await asyncio.gather(
    exchange.fetch_ohlcv(...),
    exchange.fetch_ticker(...),
    exchange.fetch_funding_rate(...)
)
```

### Red Flags

- [ ] Unreadable query count in tests (indicates N+1)
- [ ] Query execution time > 100ms
- [ ] Cache hit rate < 50% for cached operations
- [ ] Connection pool errors in logs
- [ ] Memory usage growing over time
- [ ] Dashboard endpoint > 200ms
- [ ] Async code without `await`
- [ ] Generic `except Exception` clauses

---

**Last Updated:** 2026-01-19
**Owner:** Ralph Loop + Claude AI
**Maintenance:** Quarterly review
