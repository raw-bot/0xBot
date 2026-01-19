"""Query performance analyzer for processing structured logs."""

import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class QueryMetrics:
    """Aggregated query metrics."""

    operation: str
    count: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    n_plus_one_alerts: int
    slow_query_alerts: int


class QueryAnalyzer:
    """Analyze query performance from structured logs."""

    def __init__(self, slow_query_threshold_ms: int = 50, n_plus_one_threshold: int = 5):
        """Initialize analyzer.

        Args:
            slow_query_threshold_ms: Threshold for slow query alerts
            n_plus_one_threshold: Threshold for N+1 query alerts
        """
        self.slow_query_threshold = slow_query_threshold_ms
        self.n_plus_one_threshold = n_plus_one_threshold
        self.metrics_by_operation: Dict[str, List[Dict]] = defaultdict(list)

    def process_log_line(self, line: str) -> None:
        """Process a single JSON log line.

        Args:
            line: JSON-formatted log line
        """
        try:
            log_entry = json.loads(line)

            # Only process query profile entries
            if log_entry.get('type') != 'query_profile':
                return

            operation = log_entry.get('operation', 'unknown')
            self.metrics_by_operation[operation].append(log_entry)

        except json.JSONDecodeError:
            # Skip non-JSON lines
            pass

    def analyze(self) -> Dict[str, QueryMetrics]:
        """Analyze collected metrics.

        Returns:
            Dictionary of operation name to QueryMetrics
        """
        results = {}

        for operation, entries in self.metrics_by_operation.items():
            query_counts = [e.get('query_count', 0) for e in entries]
            query_times = [e.get('query_time_ms', 0) for e in entries]

            n_plus_one_count = sum(1 for e in entries if e.get('query_count', 0) > self.n_plus_one_threshold)
            slow_query_count = sum(1 for e in entries if e.get('query_time_ms', 0) > self.slow_query_threshold)

            results[operation] = QueryMetrics(
                operation=operation,
                count=len(entries),
                total_time_ms=sum(query_times),
                avg_time_ms=sum(query_times) / len(query_times) if query_times else 0,
                min_time_ms=min(query_times) if query_times else 0,
                max_time_ms=max(query_times) if query_times else 0,
                n_plus_one_alerts=n_plus_one_count,
                slow_query_alerts=slow_query_count,
            )

        return results

    def print_report(self) -> None:
        """Print analysis report to stdout."""
        metrics = self.analyze()

        if not metrics:
            print("No query metrics found")
            return

        # Sort by average time (slowest first)
        sorted_metrics = sorted(metrics.values(), key=lambda m: m.avg_time_ms, reverse=True)

        print("\n" + "=" * 100)
        print("QUERY PERFORMANCE REPORT")
        print("=" * 100)

        print(f"\n{'Operation':<40} {'Count':<8} {'Avg':<8} {'Min':<8} {'Max':<8} {'Alerts':<8}")
        print("-" * 100)

        for metric in sorted_metrics:
            alerts = f"N+1:{metric.n_plus_one_alerts} Slow:{metric.slow_query_alerts}"
            print(
                f"{metric.operation:<40} {metric.count:<8} "
                f"{metric.avg_time_ms:<8.1f} {metric.min_time_ms:<8.1f} "
                f"{metric.max_time_ms:<8.1f} {alerts:<8}"
            )

        print("\n" + "=" * 100)

        # Print alerts
        alerts = [m for m in sorted_metrics if m.n_plus_one_alerts > 0 or m.slow_query_alerts > 0]
        if alerts:
            print("\n⚠️  ALERTS:")
            for metric in alerts:
                if metric.n_plus_one_alerts > 0:
                    print(f"  🔴 {metric.operation}: {metric.n_plus_one_alerts} N+1 detections")
                if metric.slow_query_alerts > 0:
                    print(f"  🟡 {metric.operation}: {metric.slow_query_alerts} slow queries")


if __name__ == "__main__":
    analyzer = QueryAnalyzer()

    # Read from stdin or file
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            for line in f:
                analyzer.process_log_line(line)
    else:
        for line in sys.stdin:
            analyzer.process_log_line(line)

    analyzer.print_report()
