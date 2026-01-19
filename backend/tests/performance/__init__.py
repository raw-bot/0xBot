"""Performance tests for dashboard and query optimization.

Tests verify:
- Query counts are minimized (no N+1 queries)
- Response times meet performance targets (<50ms p95)
- Pagination works correctly
- All data structures are complete
"""
