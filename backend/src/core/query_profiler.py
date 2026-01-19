"""Query profiling for detecting N+1 query patterns."""

import logging
import time
from contextvars import ContextVar
from typing import Optional

logger = logging.getLogger(__name__)

# Context variables for tracking query statistics in async context
_query_count: ContextVar[int] = ContextVar('query_count', default=0)
_query_times: ContextVar[list] = ContextVar('query_times', default=[])
_operation_name: ContextVar[str] = ContextVar('operation_name', default='unknown')


class QueryProfiler:
    """Helper class for tracking and logging query performance."""

    @staticmethod
    def start_operation(operation_name: str) -> None:
        """Mark the start of an operation."""
        _operation_name.set(operation_name)
        _query_count.set(0)
        _query_times.set([])

    @staticmethod
    def record_query(query_time_ms: float) -> None:
        """Record a query execution time."""
        current_count = _query_count.get()
        _query_count.set(current_count + 1)

        times = _query_times.get()
        times.append(query_time_ms)
        _query_times.set(times)

    @staticmethod
    def end_operation() -> dict:
        """End operation and return statistics."""
        query_count = _query_count.get()
        query_times = _query_times.get()
        operation_name = _operation_name.get()

        stats = {
            'operation': operation_name,
            'query_count': query_count,
            'total_time_ms': sum(query_times) if query_times else 0,
            'avg_time_ms': (sum(query_times) / len(query_times)) if query_times else 0,
            'max_time_ms': max(query_times) if query_times else 0,
            'min_time_ms': min(query_times) if query_times else 0,
        }

        # Reset context
        _query_count.set(0)
        _query_times.set([])
        _operation_name.set('unknown')

        return stats

    @staticmethod
    def log_stats(stats: dict, threshold_query_count: int = 5) -> None:
        """Log query statistics and warn if exceeds thresholds."""
        query_count = stats['query_count']
        total_time = stats['total_time_ms']
        operation = stats['operation']

        # Warn on excessive query count (potential N+1)
        if query_count > threshold_query_count:
            logger.warning(
                f"[QUERY PROFILE] {operation}: {query_count} queries ({total_time:.1f}ms) - "
                f"POTENTIAL N+1 (>5 queries)"
            )
        # Log slow queries
        elif total_time > 50:
            logger.warning(
                f"[QUERY PROFILE] {operation}: {query_count} queries ({total_time:.1f}ms) - "
                f"SLOW (>50ms)"
            )
        # Log normal operations
        elif query_count > 1:
            logger.info(
                f"[QUERY PROFILE] {operation}: {query_count} queries ({total_time:.1f}ms)"
            )


def profile_operation(operation_name: str, threshold_query_count: int = 5):
    """Decorator to profile async operations for N+1 queries.

    Usage:
        @profile_operation("dashboard_load")
        async def get_dashboard_data(db: AsyncSession):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            QueryProfiler.start_operation(operation_name)
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                stats = QueryProfiler.end_operation()
                QueryProfiler.log_stats(stats, threshold_query_count)
        return wrapper
    return decorator
