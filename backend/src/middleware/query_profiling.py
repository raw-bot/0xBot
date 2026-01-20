"""Query profiling middleware for tracking and logging database queries."""

import json
import logging
import time
from typing import Any, Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.query_profiler import QueryProfiler

logger = logging.getLogger(__name__)


class QueryProfilingMiddleware(BaseHTTPMiddleware):
    """Middleware to profile database queries per request.

    Tracks:
    - Query count per request
    - Query execution times
    - Slow queries (>50ms)
    - Excessive query counts (potential N+1)
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Profile queries during request processing."""
        # Determine operation name from request
        operation_name = f"{request.method} {request.url.path}"

        # Start profiling operation
        QueryProfiler.start_operation(operation_name)
        request_start_time = time.time()

        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            # Always log metrics, even if exception occurs
            try:
                stats: dict[str, Any] = QueryProfiler.end_operation()
                request_duration_ms = (time.time() - request_start_time) * 1000

                # Enhance stats with request info
                stats['request_method'] = request.method
                stats['request_path'] = request.url.path
                stats['request_duration_ms'] = request_duration_ms

                # Log statistics
                QueryProfiler.log_stats(stats, threshold_query_count=5)

                # Structured logging for monitoring
                self._log_structured_metrics(stats)
            except Exception:
                # Silently ignore any profiling errors - don't interfere with request handling
                pass

    @staticmethod
    def _log_structured_metrics(stats: dict[str, Any]) -> None:
        """Log metrics in structured JSON format for monitoring systems."""
        metrics = {
            'type': 'query_profile',
            'timestamp': time.time(),
            'operation': stats.get('operation'),
            'query_count': stats.get('query_count'),
            'query_time_ms': stats.get('total_time_ms'),
            'request_duration_ms': stats.get('request_duration_ms'),
            'avg_query_time_ms': stats.get('avg_time_ms'),
            'max_query_time_ms': stats.get('max_time_ms'),
            'min_query_time_ms': stats.get('min_time_ms'),
            'request_method': stats.get('request_method'),
            'request_path': stats.get('request_path'),
        }

        # Log as JSON for easy parsing by monitoring systems
        logger.info(json.dumps(metrics))
