#!/usr/bin/env python3
"""Automated log analysis for production audit."""
import argparse
import json
import re
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any


class AuditMonitor:
    def __init__(self, log_directory: str = "logs"):
        self.log_directory = Path(log_directory)
        self.metrics = {
            "cycles_completed": 0,
            "positions_opened": 0,
            "positions_closed": 0,
            "capital_drift_alerts": 0,
            "errors_count": 0,
            "llm_decisions": 0,
            "trades_executed": 0,
            "max_positions_held": 0,
            "capital_drift_max": Decimal("0"),
            "sl_tp_triggers": 0,
            "emergency_closes": 0,
        }

    def analyze_recent_logs(self, hours: int = 24) -> dict[str, Any]:
        print(f"Analyzing logs ({hours}h)...")

        log_files = self._find_recent_log_files(hours)
        if not log_files:
            return {"error": f"No log files found for past {hours} hours"}

        for log_file in log_files:
            self._analyze_log_file(log_file)

        self._calculate_final_metrics()
        return self._generate_report()

    def _find_recent_log_files(self, hours: int) -> list[Path]:
        if not self.log_directory.exists():
            return []

        cutoff = datetime.now() - timedelta(hours=hours)
        log_files = [
            f for f in self.log_directory.glob("*.log")
            if f.stat().st_mtime > cutoff.timestamp()
        ]
        return sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)

    def _analyze_log_file(self, log_file: Path) -> None:
        print(f"  Analyzing {log_file.name}...")
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    self._parse_log_line(line.strip())
        except Exception as e:
            print(f"  Error reading {log_file.name}: {e}")

    def _parse_log_line(self, line: str) -> None:
        m = self.metrics

        if "Cycle" in line and "completed" in line.lower():
            m["cycles_completed"] += 1
        if "METRICS |" in line:
            self._parse_metrics_line(line)
        if "BUY" in line and ("✅" in line or "SUCCESS" in line.upper()):
            m["positions_opened"] += 1
        if "EXIT" in line and ("✅" in line or "SUCCESS" in line.upper()):
            m["positions_closed"] += 1
        if "EXIT TRIGGERED" in line:
            m["sl_tp_triggers"] += 1
        if "❌" in line or "ERROR" in line.upper():
            m["errors_count"] += 1
        if "🧠" in line and any(x in line for x in ["ENTRY", "EXIT", "HOLD"]):
            m["llm_decisions"] += 1
        if "EMERGENCY CLOSE" in line:
            m["emergency_closes"] += 1

    def _parse_metrics_line(self, line: str) -> None:
        try:
            positions = re.search(r"Positions: (\d+)", line)
            drift = re.search(r"Drift: \$([0-9,.]+)", line)

            if positions:
                count = int(positions.group(1))
                self.metrics["max_positions_held"] = max(
                    self.metrics["max_positions_held"], count
                )

            if drift:
                value = Decimal(drift.group(1).replace(",", ""))
                self.metrics["capital_drift_max"] = max(
                    self.metrics["capital_drift_max"], value
                )
                if value > Decimal("0.01"):
                    self.metrics["capital_drift_alerts"] += 1
        except Exception:
            pass

    def _calculate_final_metrics(self) -> None:
        self.metrics["trades_executed"] = self.metrics["positions_opened"]

        closed = self.metrics["positions_closed"]
        if closed > 0:
            self.metrics["sl_tp_success_rate"] = (
                self.metrics["sl_tp_triggers"] / closed
            ) * 100
        else:
            self.metrics["sl_tp_success_rate"] = 0

    def _generate_report(self) -> dict[str, Any]:
        criteria = self._evaluate_success_criteria()
        return {
            "timestamp": datetime.now().isoformat(),
            "period_analyzed": "24h",
            "metrics": self.metrics,
            "success_criteria": criteria,
            "recommendations": self._generate_recommendations(),
            "alerts": self._check_alerts(),
        }

    def _evaluate_success_criteria(self) -> dict[str, Any]:
        m = self.metrics

        criteria = {
            "no_crashes_24h": {
                "target": "0 crashes",
                "actual": m["errors_count"],
                "status": "PASS" if m["errors_count"] == 0 else "FAIL",
            },
            "sl_tp_triggers_active": {
                "target": "> 0 SL/TP triggers",
                "actual": m["sl_tp_triggers"],
                "status": "PASS" if m["sl_tp_triggers"] > 0 else "FAIL",
            },
            "capital_drift_controlled": {
                "target": "< $0.01 max drift",
                "actual": f"${m['capital_drift_max']}",
                "status": "PASS" if m["capital_drift_max"] <= Decimal("0.01") else "FAIL",
            },
            "positions_closed_timely": {
                "target": "Max 3 positions",
                "actual": f"{m['max_positions_held']} positions",
                "status": "PASS" if m["max_positions_held"] <= 3 else "WARNING",
            },
            "trading_cycles_active": {
                "target": "> 10 cycles",
                "actual": m["cycles_completed"],
                "status": "PASS" if m["cycles_completed"] > 10 else "FAIL",
            },
        }

        passed = sum(1 for c in criteria.values() if c["status"] == "PASS")
        total = len(criteria)
        score = (passed / total) * 100

        if score >= 80:
            overall_status = "PRODUCTION READY"
        elif score >= 60:
            overall_status = "NEEDS ATTENTION"
        else:
            overall_status = "CRITICAL ISSUES"

        criteria["overall_score"] = {
            "score": f"{score:.1f}%",
            "passed": passed,
            "total": total,
            "status": overall_status,
        }

        return criteria

    def _check_alerts(self) -> list[str]:
        m = self.metrics
        alerts = []

        if m["errors_count"] > 5:
            alerts.append(f"HIGH ERROR COUNT: {m['errors_count']} errors")
        if m["capital_drift_max"] > Decimal("0.1"):
            alerts.append(f"CAPITAL DRIFT: ${m['capital_drift_max']} exceeds $0.10")
        if m["emergency_closes"] > 0:
            alerts.append(f"EMERGENCY CLOSES: {m['emergency_closes']}")
        if m["cycles_completed"] == 0:
            alerts.append("NO TRADING CYCLES: Bot may not be running")
        if m["sl_tp_triggers"] == 0 and m["positions_opened"] > 0:
            alerts.append("NO SL/TP TRIGGERS: Risk management may be inactive")

        return alerts

    def _generate_recommendations(self) -> list[str]:
        m = self.metrics
        recs = []

        if m["errors_count"] > 0:
            recs.append("Investigate errors in logs")
        if m["capital_drift_max"] > Decimal("0.01"):
            recs.append("Verify capital calculation integrity")
        if m["sl_tp_triggers"] == 0:
            recs.append("Check SL/TP configuration")
        if m["cycles_completed"] < 12:
            recs.append("Verify bot is running (expected 1 cycle per 5min)")
        if m["max_positions_held"] > 3:
            recs.append("Consider reducing max simultaneous positions")

        return recs

    def run_quick_test(self, minutes: int = 30) -> dict[str, Any]:
        print(f"Quick validation test ({minutes} minutes)...")
        report = self.analyze_recent_logs(hours=minutes / 60)

        if "success_criteria" in report:
            criteria = report["success_criteria"]
            criteria["no_crashes_24h"]["target"] = f"0 crashes in {minutes}min"
            expected_cycles = minutes // 5
            criteria["trading_cycles_active"]["target"] = f"> {expected_cycles} cycles"
            criteria["trading_cycles_active"]["status"] = (
                "PASS" if self.metrics["cycles_completed"] > expected_cycles else "FAIL"
            )

        report["test_type"] = f"quick_test_{minutes}min"
        return report


def print_report(report: dict[str, Any]) -> None:
    print("\n" + "=" * 60)
    print("AUDIT REPORT")
    print("=" * 60)

    print(f"Period: {report.get('period_analyzed', 'N/A')}")
    overall = report.get("success_criteria", {}).get("overall_score", {})
    print(f"Score: {overall.get('score', 'N/A')} - {overall.get('status', 'N/A')}")

    print("\nCRITERIA:")
    for key, value in report.get("success_criteria", {}).items():
        if key != "overall_score":
            print(f"  {key}: {value['status']} ({value['actual']} / {value['target']})")

    if report.get("alerts"):
        print("\nALERTS:")
        for alert in report["alerts"]:
            print(f"  - {alert}")

    if report.get("recommendations"):
        print("\nRECOMMENDATIONS:")
        for rec in report["recommendations"]:
            print(f"  - {rec}")


def main():
    parser = argparse.ArgumentParser(description="Audit Monitoring")
    parser.add_argument("--hours", type=int, default=24, help="Hours to analyze")
    parser.add_argument("--quick-test", type=int, help="Quick test in minutes")
    parser.add_argument("--log-dir", default="logs", help="Log directory")
    args = parser.parse_args()

    monitor = AuditMonitor(args.log_dir)

    if args.quick_test:
        report = monitor.run_quick_test(args.quick_test)
    else:
        report = monitor.analyze_recent_logs(args.hours)

    print_report(report)

    report_file = f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved: {report_file}")

    score = float(report.get("success_criteria", {}).get("overall_score", {}).get("score", "0%").rstrip("%"))
    exit(0 if score >= 80 else 1)


if __name__ == "__main__":
    main()
