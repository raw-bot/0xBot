"""Tests for query profiling middleware."""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from src.core.query_profiler import QueryProfiler
from src.middleware.query_profiling import QueryProfilingMiddleware


@pytest.fixture
def app_with_profiling():
    """Create a test FastAPI app with query profiling middleware."""
    app = FastAPI()
    app.add_middleware(QueryProfilingMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    @app.get("/test-slow")
    async def test_slow_endpoint():
        # Simulate slow operation
        import time
        time.sleep(0.1)
        return {"status": "slow"}

    return app


@pytest.fixture
def client(app_with_profiling):
    """Create test client."""
    return TestClient(app_with_profiling)


class TestQueryProfilingMiddleware:
    """Test query profiling middleware functionality."""

    def test_middleware_processes_request(self, client):
        """Test that middleware processes requests."""
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_middleware_records_operation_name(self, client):
        """Test that middleware records operation names."""
        with patch('backend.src.middleware.query_profiling.QueryProfiler.start_operation') as mock_start, \
             patch('backend.src.middleware.query_profiling.QueryProfiler.end_operation') as mock_end:
            mock_end.return_value = {
                'operation': 'GET /test',
                'query_count': 0,
                'total_time_ms': 0,
                'avg_time_ms': 0,
                'max_time_ms': 0,
                'min_time_ms': 0,
            }

            response = client.get("/test")
            assert response.status_code == 200

            mock_start.assert_called_once_with("GET /test")

    def test_middleware_ends_operation(self, client):
        """Test that middleware ends operation and retrieves stats."""
        with patch('backend.src.middleware.query_profiling.QueryProfiler.end_operation') as mock_end, \
             patch('backend.src.middleware.query_profiling.QueryProfiler.log_stats'):
            mock_end.return_value = {
                'operation': 'GET /test',
                'query_count': 2,
                'total_time_ms': 25.5,
                'avg_time_ms': 12.75,
                'max_time_ms': 15.5,
                'min_time_ms': 10.0,
            }

            response = client.get("/test")
            assert response.status_code == 200

            mock_end.assert_called_once()

    def test_middleware_logs_stats(self, client):
        """Test that middleware logs statistics."""
        with patch('backend.src.middleware.query_profiling.QueryProfiler.log_stats') as mock_log:
            response = client.get("/test")
            assert response.status_code == 200

            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            stats = args[0]
            assert 'operation' in stats
            assert 'query_count' in stats
            assert 'total_time_ms' in stats

    def test_middleware_includes_request_info(self, client):
        """Test that middleware includes request info in stats."""
        with patch('backend.src.middleware.query_profiling.QueryProfilingMiddleware._log_structured_metrics') as mock_metrics:
            response = client.get("/test")
            assert response.status_code == 200

            mock_metrics.assert_called_once()
            stats = mock_metrics.call_args[0][0]
            assert stats['request_method'] == 'GET'
            assert stats['request_path'] == '/test'

    def test_middleware_calculates_request_duration(self, client):
        """Test that middleware calculates request duration."""
        with patch('backend.src.middleware.query_profiling.QueryProfilingMiddleware._log_structured_metrics') as mock_metrics:
            response = client.get("/test")
            assert response.status_code == 200

            mock_metrics.assert_called_once()
            stats = mock_metrics.call_args[0][0]
            assert 'request_duration_ms' in stats
            assert stats['request_duration_ms'] >= 0

    def test_structured_logging_includes_all_fields(self):
        """Test that structured logging includes all required fields."""
        middleware = QueryProfilingMiddleware(app=MagicMock(), dispatch=MagicMock())
        stats = {
            'operation': 'GET /dashboard',
            'query_count': 3,
            'total_time_ms': 45.2,
            'avg_time_ms': 15.1,
            'max_time_ms': 20.5,
            'min_time_ms': 10.1,
            'request_method': 'GET',
            'request_path': '/dashboard',
            'request_duration_ms': 50.0,
        }

        with patch('backend.src.middleware.query_profiling.logger.info') as mock_log:
            middleware._log_structured_metrics(stats)
            mock_log.assert_called_once()

            logged_data = json.loads(mock_log.call_args[0][0])
            assert logged_data['type'] == 'query_profile'
            assert logged_data['operation'] == 'GET /dashboard'
            assert logged_data['query_count'] == 3
            assert logged_data['query_time_ms'] == 45.2
            assert logged_data['request_method'] == 'GET'
            assert logged_data['request_path'] == '/dashboard'


class TestQueryProfiler:
    """Test QueryProfiler functionality."""

    def test_profiler_starts_operation(self):
        """Test starting an operation."""
        QueryProfiler.start_operation("test_operation")
        # Just verify it doesn't raise

    def test_profiler_records_query(self):
        """Test recording a query."""
        QueryProfiler.start_operation("test_operation")
        QueryProfiler.record_query(25.5)
        stats = QueryProfiler.end_operation()
        assert stats['query_count'] == 1
        assert stats['total_time_ms'] == 25.5

    def test_profiler_tracks_multiple_queries(self):
        """Test tracking multiple queries."""
        QueryProfiler.start_operation("test_operation")
        QueryProfiler.record_query(10.0)
        QueryProfiler.record_query(20.0)
        QueryProfiler.record_query(15.0)
        stats = QueryProfiler.end_operation()

        assert stats['query_count'] == 3
        assert stats['total_time_ms'] == 45.0
        assert stats['avg_time_ms'] == 15.0
        assert stats['max_time_ms'] == 20.0
        assert stats['min_time_ms'] == 10.0

    def test_profiler_resets_after_end_operation(self):
        """Test that profiler resets after ending operation."""
        QueryProfiler.start_operation("operation1")
        QueryProfiler.record_query(10.0)
        stats1 = QueryProfiler.end_operation()

        assert stats1['query_count'] == 1

        QueryProfiler.start_operation("operation2")
        stats2 = QueryProfiler.end_operation()

        assert stats2['query_count'] == 0

    def test_profiler_logs_normal_operations(self, caplog):
        """Test that profiler logs normal operations."""
        QueryProfiler.start_operation("normal_op")
        QueryProfiler.record_query(10.0)
        QueryProfiler.record_query(20.0)
        stats = QueryProfiler.end_operation()

        with patch('backend.src.core.query_profiler.logger.info') as mock_info:
            QueryProfiler.log_stats(stats)
            mock_info.assert_called_once()

    def test_profiler_logs_slow_queries(self):
        """Test that profiler logs slow queries."""
        QueryProfiler.start_operation("slow_op")
        QueryProfiler.record_query(60.0)
        stats = QueryProfiler.end_operation()

        with patch('backend.src.core.query_profiler.logger.warning') as mock_warning:
            QueryProfiler.log_stats(stats)
            mock_warning.assert_called_once()
            assert "SLOW" in mock_warning.call_args[0][0]

    def test_profiler_logs_n_plus_one_queries(self):
        """Test that profiler logs potential N+1 queries."""
        QueryProfiler.start_operation("n_plus_one_op")
        for i in range(10):
            QueryProfiler.record_query(5.0)
        stats = QueryProfiler.end_operation()

        with patch('backend.src.core.query_profiler.logger.warning') as mock_warning:
            QueryProfiler.log_stats(stats)
            mock_warning.assert_called_once()
            assert "N+1" in mock_warning.call_args[0][0]


class TestStructuredLogging:
    """Test structured logging functionality."""

    def test_json_formatter_formats_correctly(self):
        """Test JSON formatter output."""
        import logging
        from src.core.logging_config import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data['level'] == 'INFO'
        assert data['logger'] == 'test'
        assert data['message'] == 'Test message'
        assert 'timestamp' in data

    def test_structured_logger_logs_query_metrics(self):
        """Test structured logger logs query metrics."""
        from src.core.logging_config import StructuredLogger

        logger = StructuredLogger("test")
        with patch('backend.src.core.logging_config.logging.getLogger') as mock_get:
            mock_logger = MagicMock()
            mock_get.return_value = mock_logger

            logger.logger = mock_logger
            logger.log_query_metrics(
                operation="test_op",
                query_count=2,
                query_time_ms=25.0,
                request_method="GET",
                request_path="/test",
            )

            mock_logger.log.assert_called_once()

    def test_slow_query_logging(self):
        """Test slow query logging."""
        from src.core.logging_config import StructuredLogger

        logger = StructuredLogger("test")
        with patch.object(logger.logger, 'warning') as mock_warning:
            logger.log_slow_query(
                query="SELECT * FROM test",
                execution_time_ms=100.0,
                threshold_ms=50,
            )

            mock_warning.assert_called_once()
            assert "SLOW QUERY" in mock_warning.call_args[0][0]
