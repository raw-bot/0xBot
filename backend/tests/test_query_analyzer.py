"""Tests for query analyzer monitoring tool."""

import json

import pytest

from backend.monitoring.query_analyzer import QueryAnalyzer, QueryMetrics


@pytest.fixture
def analyzer():
    """Create a QueryAnalyzer instance."""
    return QueryAnalyzer(slow_query_threshold_ms=50, n_plus_one_threshold=5)


class TestQueryAnalyzer:
    """Test QueryAnalyzer functionality."""

    def test_analyzer_initializes(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer.slow_query_threshold == 50
        assert analyzer.n_plus_one_threshold == 5
        assert len(analyzer.metrics_by_operation) == 0

    def test_analyzer_processes_json_log_line(self, analyzer):
        """Test processing JSON log lines."""
        log_line = json.dumps({
            'type': 'query_profile',
            'operation': 'test_op',
            'query_count': 2,
            'query_time_ms': 25.0,
        })

        analyzer.process_log_line(log_line)
        assert 'test_op' in analyzer.metrics_by_operation
        assert len(analyzer.metrics_by_operation['test_op']) == 1

    def test_analyzer_skips_non_json_lines(self, analyzer):
        """Test that analyzer skips non-JSON lines."""
        analyzer.process_log_line("not json")
        assert len(analyzer.metrics_by_operation) == 0

    def test_analyzer_skips_non_query_profile_entries(self, analyzer):
        """Test that analyzer skips non-query-profile entries."""
        log_line = json.dumps({
            'type': 'other_type',
            'operation': 'test_op',
        })

        analyzer.process_log_line(log_line)
        assert len(analyzer.metrics_by_operation) == 0

    def test_analyzer_aggregates_metrics(self, analyzer):
        """Test metric aggregation."""
        for i in range(3):
            log_line = json.dumps({
                'type': 'query_profile',
                'operation': 'test_op',
                'query_count': 2,
                'query_time_ms': 25.0,
            })
            analyzer.process_log_line(log_line)

        metrics = analyzer.analyze()
        assert 'test_op' in metrics
        assert metrics['test_op'].count == 3

    def test_analyzer_calculates_averages(self, analyzer):
        """Test average calculation."""
        times = [10.0, 20.0, 30.0]
        for time_ms in times:
            log_line = json.dumps({
                'type': 'query_profile',
                'operation': 'test_op',
                'query_count': 1,
                'query_time_ms': time_ms,
            })
            analyzer.process_log_line(log_line)

        metrics = analyzer.analyze()
        assert metrics['test_op'].avg_time_ms == 20.0
        assert metrics['test_op'].min_time_ms == 10.0
        assert metrics['test_op'].max_time_ms == 30.0

    def test_analyzer_detects_slow_queries(self, analyzer):
        """Test slow query detection."""
        log_line = json.dumps({
            'type': 'query_profile',
            'operation': 'slow_op',
            'query_count': 1,
            'query_time_ms': 100.0,  # Exceeds 50ms threshold
        })
        analyzer.process_log_line(log_line)

        metrics = analyzer.analyze()
        assert metrics['slow_op'].slow_query_alerts == 1

    def test_analyzer_detects_n_plus_one_queries(self, analyzer):
        """Test N+1 query detection."""
        log_line = json.dumps({
            'type': 'query_profile',
            'operation': 'n_plus_one_op',
            'query_count': 10,  # Exceeds 5 threshold
            'query_time_ms': 50.0,
        })
        analyzer.process_log_line(log_line)

        metrics = analyzer.analyze()
        assert metrics['n_plus_one_op'].n_plus_one_alerts == 1

    def test_analyzer_handles_multiple_operations(self, analyzer):
        """Test handling multiple different operations."""
        for op in ['op1', 'op2', 'op3']:
            log_line = json.dumps({
                'type': 'query_profile',
                'operation': op,
                'query_count': 1,
                'query_time_ms': 10.0,
            })
            analyzer.process_log_line(log_line)

        metrics = analyzer.analyze()
        assert len(metrics) == 3
        assert all(op in metrics for op in ['op1', 'op2', 'op3'])

    def test_query_metrics_dataclass(self):
        """Test QueryMetrics dataclass."""
        metrics = QueryMetrics(
            operation='test',
            count=5,
            total_time_ms=100.0,
            avg_time_ms=20.0,
            min_time_ms=10.0,
            max_time_ms=30.0,
            n_plus_one_alerts=0,
            slow_query_alerts=1,
        )

        assert metrics.operation == 'test'
        assert metrics.count == 5
        assert metrics.avg_time_ms == 20.0
        assert metrics.slow_query_alerts == 1

    def test_analyzer_handles_empty_metrics(self, analyzer):
        """Test analyzer with no metrics."""
        metrics = analyzer.analyze()
        assert len(metrics) == 0

    def test_analyzer_counts_mixed_alerts(self, analyzer):
        """Test counting both slow and N+1 alerts."""
        # One slow query
        log_line = json.dumps({
            'type': 'query_profile',
            'operation': 'mixed_op',
            'query_count': 2,
            'query_time_ms': 100.0,
        })
        analyzer.process_log_line(log_line)

        # One N+1 query
        log_line = json.dumps({
            'type': 'query_profile',
            'operation': 'mixed_op',
            'query_count': 10,
            'query_time_ms': 25.0,
        })
        analyzer.process_log_line(log_line)

        metrics = analyzer.analyze()
        assert metrics['mixed_op'].slow_query_alerts == 1
        assert metrics['mixed_op'].n_plus_one_alerts == 1

    def test_analyzer_with_custom_thresholds(self):
        """Test analyzer with custom thresholds."""
        analyzer = QueryAnalyzer(slow_query_threshold_ms=100, n_plus_one_threshold=10)

        # Should not be detected as slow
        log_line = json.dumps({
            'type': 'query_profile',
            'operation': 'test_op',
            'query_count': 1,
            'query_time_ms': 75.0,
        })
        analyzer.process_log_line(log_line)

        metrics = analyzer.analyze()
        assert metrics['test_op'].slow_query_alerts == 0

        # Should be detected as N+1
        log_line = json.dumps({
            'type': 'query_profile',
            'operation': 'test_op',
            'query_count': 15,
            'query_time_ms': 75.0,
        })
        analyzer.process_log_line(log_line)

        metrics = analyzer.analyze()
        assert metrics['test_op'].n_plus_one_alerts == 1
