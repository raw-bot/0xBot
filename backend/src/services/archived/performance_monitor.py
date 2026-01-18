"""Service de monitoring de performance pour le bot de trading."""

import time
import psutil
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from decimal import Decimal

from ..core.logger import get_logger


class PerformanceMonitor:
    """Moniteur de performance en temps réel."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.start_time = time.time()
        self.metrics = {
            "cycles_executed": 0,
            "total_trades": 0,
            "successful_trades": 0,
            "failed_trades": 0,
            "total_profit": Decimal("0"),
            "memory_usage_mb": 0,
            "cpu_usage_percent": 0,
            "average_cycle_time": 0,
            "cache_hit_rate": 0.0
        }
        self.cycle_times = []
        
    async def record_cycle(self, cycle_duration: float, trades_executed: int = 0) -> None:
        """Enregistre les métriques d'un cycle."""
        self.metrics["cycles_executed"] += 1
        self.cycle_times.append(cycle_duration)
        
        # Garder seulement les 100 derniers temps de cycle
        if len(self.cycle_times) > 100:
            self.cycle_times.pop(0)
        
        self.metrics["average_cycle_time"] = sum(self.cycle_times) / len(self.cycle_times)
        self.metrics["total_trades"] += trades_executed
        
        # Mise à jour des métriques système
        process = psutil.Process()
        self.metrics["memory_usage_mb"] = process.memory_info().rss / 1024 / 1024
        self.metrics["cpu_usage_percent"] = process.cpu_percent()
        
        self.logger.info(f"PERF | Cycle {self.metrics['cycles_executed']} | "
                        f"Duration: {cycle_duration:.1f}s | "
                        f"Average: {self.metrics['average_cycle_time']:.1f}s | "
                        f"Memory: {self.metrics['memory_usage_mb']:.1f}MB")
    
    def record_trade(self, success: bool, profit: Decimal = Decimal("0")) -> None:
        """Enregistre les métriques d'un trade."""
        if success:
            self.metrics["successful_trades"] += 1
        else:
            self.metrics["failed_trades"] += 1
        
        self.metrics["total_profit"] += profit
        self.metrics["cache_hit_rate"] = min(1.0, self.metrics["cache_hit_rate"] + 0.01)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Génère un rapport de performance."""
        uptime = time.time() - self.start_time
        uptime_hours = uptime / 3600
        
        success_rate = (self.metrics["successful_trades"] / 
                       max(1, self.metrics["total_trades"]) * 100)
        
        return {
            "uptime_hours": round(uptime_hours, 2),
            "cycles_per_hour": round(self.metrics["cycles_executed"] / max(0.1, uptime_hours), 1),
            "success_rate_percent": round(success_rate, 1),
            "total_profit": float(self.metrics["total_profit"]),
            "average_cycle_time_sec": round(self.metrics["average_cycle_time"], 2),
            "memory_usage_mb": round(self.metrics["memory_usage_mb"], 1),
            "cpu_usage_percent": round(self.metrics["cpu_usage_percent"], 1),
            "cache_hit_rate_percent": round(self.metrics["cache_hit_rate"] * 100, 1)
        }
    
    def log_performance_summary(self) -> None:
        """Log un résumé de performance."""
        report = self.get_performance_report()
        
        self.logger.info("=== PERFORMANCE SUMMARY ===")
        self.logger.info(f"Uptime: {report['uptime_hours']}h")
        self.logger.info(f"Cycles/hour: {report['cycles_per_hour']}")
        self.logger.info(f"Success rate: {report['success_rate_percent']}%")
        self.logger.info(f"Total profit: ${report['total_profit']:.2f}")
        self.logger.info(f"Avg cycle time: {report['average_cycle_time_sec']}s")
        self.logger.info(f"Memory: {report['memory_usage_mb']}MB")
        self.logger.info(f"Cache hit rate: {report['cache_hit_rate_percent']}%")
        self.logger.info("============================")


# Instance globale du moniteur
performance_monitor = PerformanceMonitor()
