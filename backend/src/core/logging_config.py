"""Structured logging configuration for performance monitoring."""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict

# Custom JSON formatter for structured logging
class JSONFormatter(logging.Formatter):
    """Format log records as JSON for easy parsing by monitoring systems."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, 'query_count'):
            log_data['query_count'] = record.query_count
        if hasattr(record, 'query_time_ms'):
            log_data['query_time_ms'] = record.query_time_ms
        if hasattr(record, 'operation'):
            log_data['operation'] = record.operation

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class StructuredLogger:
    """Helper class for structured logging with context."""

    def __init__(self, name: str):
        """Initialize structured logger."""
        self.logger = logging.getLogger(name)

    def log_query_metrics(
        self,
        operation: str,
        query_count: int,
        query_time_ms: float,
        request_method: str = None,
        request_path: str = None,
        user_id: str = None,
        bot_id: str = None,
    ) -> None:
        """Log query metrics in structured format.

        Args:
            operation: Name of the operation (e.g., 'dashboard_load')
            query_count: Number of queries executed
            query_time_ms: Total query execution time in milliseconds
            request_method: HTTP method (e.g., 'GET', 'POST')
            request_path: HTTP path
            user_id: User ID for context
            bot_id: Bot ID for context
        """
        metrics = {
            'type': 'query_profile',
            'operation': operation,
            'query_count': query_count,
            'query_time_ms': query_time_ms,
        }

        if request_method:
            metrics['request_method'] = request_method
        if request_path:
            metrics['request_path'] = request_path
        if user_id:
            metrics['user_id'] = user_id
        if bot_id:
            metrics['bot_id'] = bot_id

        # Determine log level based on metrics
        if query_count > 5:
            level = logging.WARNING
            message = f"Potential N+1 queries detected: {query_count} queries in {operation}"
        elif query_time_ms > 50:
            level = logging.WARNING
            message = f"Slow query operation: {query_time_ms}ms for {operation}"
        else:
            level = logging.INFO
            message = f"Query metrics: {operation} ({query_count} queries, {query_time_ms}ms)"

        self.logger.log(level, message, extra=metrics)

    def log_slow_query(
        self,
        query: str,
        execution_time_ms: float,
        threshold_ms: int = 50,
    ) -> None:
        """Log a slow query that exceeded threshold.

        Args:
            query: The SQL query
            execution_time_ms: Query execution time in milliseconds
            threshold_ms: Threshold for considering a query slow
        """
        if execution_time_ms > threshold_ms:
            self.logger.warning(
                f"SLOW QUERY: {execution_time_ms}ms (threshold: {threshold_ms}ms)\n{query}"
            )


def configure_structured_logging(log_level: str = 'INFO') -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Create console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Use JSON formatter for structured output
    formatter = JSONFormatter()
    console_handler.setFormatter(formatter)

    # Add handler to root logger
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)

    # Configure specific loggers
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.INFO)

    return root_logger


# Helper functions for common logging patterns
def log_query_count_alert(
    operation: str,
    query_count: int,
    threshold: int = 5,
) -> None:
    """Alert if query count exceeds threshold (potential N+1).

    Args:
        operation: Name of the operation
        query_count: Actual query count
        threshold: Alert threshold
    """
    logger = logging.getLogger(__name__)
    if query_count > threshold:
        logger.warning(
            f"[N+1 ALERT] {operation}: {query_count} queries (threshold: {threshold})"
        )


def log_slow_query_alert(
    operation: str,
    execution_time_ms: float,
    threshold_ms: int = 50,
) -> None:
    """Alert if query execution time exceeds threshold.

    Args:
        operation: Name of the operation
        execution_time_ms: Actual execution time
        threshold_ms: Alert threshold
    """
    logger = logging.getLogger(__name__)
    if execution_time_ms > threshold_ms:
        logger.warning(
            f"[SLOW QUERY] {operation}: {execution_time_ms}ms (threshold: {threshold_ms}ms)"
        )
