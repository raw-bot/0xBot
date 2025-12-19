"""Service d'export des métriques pour monitoring externe."""

import json
import csv
from datetime import datetime, timedelta
from typing import Dict, Any, List
from decimal import Decimal

from ..core.logger import get_logger


class MetricsExportService:
    """Service d'export des métriques."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def export_to_json(self, data: Dict[str, Any], filename: str = None) -> str:
        """Exporte les métriques en JSON."""
        if filename is None:
            filename = f"metrics_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = f"exports/{filename}"
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        self.logger.info(f"Metrics exported to {filepath}")
        return filepath
    
    def export_to_csv(self, trades_data: List[Dict], filename: str = None) -> str:
        """Exporte les données de trades en CSV."""
        if filename is None:
            filename = f"trades_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = f"exports/{filename}"
        
        # Créer le répertoire exports s'il n'existe pas
        import os
        os.makedirs("exports", exist_ok=True)
        
        if trades_data:
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=trades_data[0].keys())
                writer.writeheader()
                writer.writerows(trades_data)
        
        self.logger.info(f"Trades data exported to {filepath}")
        return filepath
    
    def generate_performance_report(self, performance_data: Dict[str, Any]) -> str:
        """Génère un rapport de performance complet."""
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_return": f"{performance_data.get('total_return', 0):.2f}%",
                "win_rate": f"{performance_data.get('win_rate', 0):.1f}%",
                "total_trades": performance_data.get('total_trades', 0),
                "profitable_trades": performance_data.get('profitable_trades', 0)
            },
            "detailed_metrics": performance_data
        }
        
        return self.export_to_json(report, "performance_report.json")
    
    def export_daily_summary(self, date: datetime = None) -> str:
        """Exporte un résumé quotidien."""
        if date is None:
            date = datetime.utcnow().date()
        
        # Logique pour récupérer les données de la journée
        summary = {
            "date": date.isoformat(),
            "total_cycles": 0,
            "total_trades": 0,
            "successful_trades": 0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0
        }
        
        return self.export_to_json(summary, f"daily_summary_{date.strftime('%Y%m%d')}.json")


# Instance globale du service d'export
metrics_export_service = MetricsExportService()
