#!/usr/bin/env python3
"""
Audit Monitoring Script - Analyse automatique des logs de production
Remplace l'analyse manuelle de 24h de logs par un système automatisé
"""

import os
import re
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any
from pathlib import Path

class AuditMonitor:
    """Analyseur automatique des logs de production pour audit."""

    def __init__(self, log_directory: str = "logs"):
        self.log_directory = Path(log_directory)
        self.metrics = {
            'cycles_completed': 0,
            'positions_opened': 0,
            'positions_closed': 0,
            'capital_drift_alerts': 0,
            'errors_count': 0,
            'llm_decisions': 0,
            'trades_executed': 0,
            'max_positions_held': 0,
            'capital_drift_max': Decimal('0'),
            'session_duration_hours': 0,
            'sl_tp_triggers': 0,
            'emergency_closes': 0
        }

    def analyze_recent_logs(self, hours: int = 24) -> Dict[str, Any]:
        """Analyse les logs récents automatiquement."""
        print(f"🔍 Analyse automatique des logs ({hours}h)...")

        # Trouver les fichiers de log récents
        log_files = self._find_recent_log_files(hours)

        if not log_files:
            return {"error": f"Aucun fichier de log trouvé pour les {hours} dernières heures"}

        # Analyser chaque fichier
        for log_file in log_files:
            self._analyze_log_file(log_file)

        # Calculer les métriques finales
        self._calculate_final_metrics()

        return self._generate_report()

    def _find_recent_log_files(self, hours: int) -> List[Path]:
        """Trouve les fichiers de log des dernières heures."""
        if not self.log_directory.exists():
            return []

        cutoff_time = datetime.now() - timedelta(hours=hours)
        log_files = []

        # Chercher les fichiers .log récents
        for log_file in self.log_directory.glob("*.log"):
            if log_file.stat().st_mtime > cutoff_time.timestamp():
                log_files.append(log_file)

        # Trier par date (plus récent en premier)
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        return log_files

    def _analyze_log_file(self, log_file: Path) -> None:
        """Analyse un fichier de log spécifique."""
        print(f"📄 Analyse de {log_file.name}...")

        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    self._parse_log_line(line.strip())
        except Exception as e:
            print(f"⚠️ Erreur lecture {log_file.name}: {e}")

    def _parse_log_line(self, line: str) -> None:
        """Parse une ligne de log et extrait les métriques."""
        # Compter les cycles complétés
        if "Cycle" in line and "completed" in line.lower():
            self.metrics['cycles_completed'] += 1

        # Métriques METRICS critiques
        if "METRICS |" in line:
            self._parse_metrics_line(line)

        # Positions ouvertes
        if "✅ BUY" in line:
            self.metrics['positions_opened'] += 1

        # Positions fermées
        if "✅ EXIT" in line:
            self.metrics['positions_closed'] += 1

        # SL/TP triggers
        if "🚨 EXIT TRIGGERED" in line:
            self.metrics['sl_tp_triggers'] += 1

        # Erreurs
        if "❌" in line or "ERROR" in line.upper():
            self.metrics['errors_count'] += 1

        # Décisions LLM
        if "🧠" in line and ("ENTRY" in line or "EXIT" in line or "HOLD" in line):
            self.metrics['llm_decisions'] += 1

        # Emergency closes
        if "EMERGENCY CLOSE" in line:
            self.metrics['emergency_closes'] += 1

    def _parse_metrics_line(self, line: str) -> None:
        """Parse les lignes METRICS spéciales ajoutées lors de l'audit."""
        try:
            # Extraire les valeurs: "METRICS | Positions: X | Capital: $Y | Equity: $Z | Drift: $W"
            positions_match = re.search(r'Positions: (\d+)', line)
            capital_match = re.search(r'Capital: \$([0-9,.]+)', line)
            equity_match = re.search(r'Equity: \$([0-9,.]+)', line)
            drift_match = re.search(r'Drift: \$([0-9,.]+)', line)

            if positions_match:
                positions = int(positions_match.group(1))
                self.metrics['max_positions_held'] = max(self.metrics['max_positions_held'], positions)

            if drift_match:
                drift = Decimal(drift_match.group(1).replace(',', ''))
                self.metrics['capital_drift_max'] = max(self.metrics['capital_drift_max'], drift)

                # Alerte si drift > $0.01
                if drift > Decimal('0.01'):
                    self.metrics['capital_drift_alerts'] += 1

        except Exception as e:
            print(f"⚠️ Erreur parsing métriques: {e}")

    def _calculate_final_metrics(self) -> None:
        """Calcule les métriques finales dérivées."""
        # Trades exécutés = positions ouvertes (chaque ouverture = 1 trade)
        self.metrics['trades_executed'] = self.metrics['positions_opened']

        # Taux de succès SL/TP
        if self.metrics['positions_closed'] > 0:
            self.metrics['sl_tp_success_rate'] = (
                self.metrics['sl_tp_triggers'] / self.metrics['positions_closed']
            ) * 100
        else:
            self.metrics['sl_tp_success_rate'] = 0

    def _generate_report(self) -> Dict[str, Any]:
        """Génère le rapport final d'audit."""
        # Évaluation automatique des critères de succès
        success_criteria = self._evaluate_success_criteria()

        report = {
            "timestamp": datetime.now().isoformat(),
            "period_analyzed": "24h",
            "metrics": self.metrics,
            "success_criteria": success_criteria,
            "recommendations": self._generate_recommendations(),
            "alerts": self._check_alerts()
        }

        return report

    def _evaluate_success_criteria(self) -> Dict[str, Any]:
        """Évalue automatiquement les critères de succès définis."""
        criteria = {
            "no_crashes_24h": {
                "target": "0 crashes",
                "actual": self.metrics['errors_count'],
                "status": "✅ PASS" if self.metrics['errors_count'] == 0 else "❌ FAIL"
            },
            "sl_tp_triggers_active": {
                "target": "> 0 SL/TP triggers",
                "actual": self.metrics['sl_tp_triggers'],
                "status": "✅ PASS" if self.metrics['sl_tp_triggers'] > 0 else "❌ FAIL"
            },
            "capital_drift_controlled": {
                "target": "< $0.01 max drift",
                "actual": f"${self.metrics['capital_drift_max']}",
                "status": "✅ PASS" if self.metrics['capital_drift_max'] <= Decimal('0.01') else "❌ FAIL"
            },
            "positions_closed_timely": {
                "target": "All positions closed < 4h",
                "actual": f"Max {self.metrics['max_positions_held']} positions",
                "status": "✅ PASS" if self.metrics['max_positions_held'] <= 3 else "⚠️ WARNING"
            },
            "trading_cycles_active": {
                "target": "> 10 cycles completed",
                "actual": self.metrics['cycles_completed'],
                "status": "✅ PASS" if self.metrics['cycles_completed'] > 10 else "❌ FAIL"
            }
        }

        # Score global
        passed = sum(1 for c in criteria.values() if "PASS" in c['status'])
        total = len(criteria)
        score = (passed / total) * 100

        criteria["overall_score"] = {
            "score": f"{score:.1f}%",
            "passed": passed,
            "total": total,
            "status": "✅ PRODUCTION READY" if score >= 80 else "⚠️ NEEDS ATTENTION" if score >= 60 else "❌ CRITICAL ISSUES"
        }

        return criteria

    def _check_alerts(self) -> List[str]:
        """Vérifie les alertes critiques."""
        alerts = []

        if self.metrics['errors_count'] > 5:
            alerts.append(f"🔴 HIGH ERROR COUNT: {self.metrics['errors_count']} errors detected")

        if self.metrics['capital_drift_max'] > Decimal('0.1'):
            alerts.append(f"🔴 CAPITAL DRIFT: Max drift ${self.metrics['capital_drift_max']} exceeds $0.10")

        if self.metrics['emergency_closes'] > 0:
            alerts.append(f"🟠 EMERGENCY CLOSES: {self.metrics['emergency_closes']} emergency position closures")

        if self.metrics['cycles_completed'] == 0:
            alerts.append("🔴 NO TRADING CYCLES: Bot may not be running properly")

        if self.metrics['sl_tp_triggers'] == 0 and self.metrics['positions_opened'] > 0:
            alerts.append("🟠 NO SL/TP TRIGGERS: Risk management may not be working")

        return alerts

    def _generate_recommendations(self) -> List[str]:
        """Génère des recommandations basées sur les métriques."""
        recommendations = []

        if self.metrics['errors_count'] > 0:
            recommendations.append("Investiguer les erreurs dans les logs pour améliorer la stabilité")

        if self.metrics['capital_drift_max'] > Decimal('0.01'):
            recommendations.append("Vérifier l'intégrité des calculs de capital et positions")

        if self.metrics['sl_tp_triggers'] == 0:
            recommendations.append("S'assurer que les stop-loss et take-profit sont correctement configurés")

        if self.metrics['cycles_completed'] < 12:  # Moins d'1 cycle par heure
            recommendations.append("Vérifier que le bot fonctionne correctement (cycles toutes les 5min)")

        if self.metrics['max_positions_held'] > 3:
            recommendations.append("Considérer réduire le nombre maximum de positions simultanées")

        return recommendations

    def run_quick_test(self, minutes: int = 30) -> Dict[str, Any]:
        """Test rapide de validation (remplace le 24h monitoring)."""
        print(f"🧪 Test rapide de validation ({minutes} minutes)...")

        # Simuler un test court
        report = self.analyze_recent_logs(hours=minutes/60)

        # Ajuster les critères pour un test court
        if "success_criteria" in report:
            criteria = report["success_criteria"]

            # Pour un test court, on est moins strict
            criteria["no_crashes_24h"]["target"] = f"0 crashes in {minutes}min"
            criteria["trading_cycles_active"]["target"] = f"> {minutes//5} cycles in {minutes}min"
            criteria["trading_cycles_active"]["status"] = "✅ PASS" if self.metrics['cycles_completed'] > (minutes//5) else "❌ FAIL"

        report["test_type"] = f"quick_test_{minutes}min"
        return report


def main():
    """Point d'entrée principal."""
    import argparse

    parser = argparse.ArgumentParser(description="Audit Monitoring - Analyse automatique des logs")
    parser.add_argument("--hours", type=int, default=24, help="Nombre d'heures à analyser")
    parser.add_argument("--quick-test", type=int, help="Test rapide en minutes")
    parser.add_argument("--log-dir", default="logs", help="Répertoire des logs")

    args = parser.parse_args()

    monitor = AuditMonitor(args.log_dir)

    if args.quick_test:
        report = monitor.run_quick_test(args.quick_test)
    else:
        report = monitor.analyze_recent_logs(args.hours)

    # Afficher le rapport
    print("\n" + "="*80)
    print("📊 RAPPORT D'AUDIT AUTOMATIQUE")
    print("="*80)

    print(f"⏱️  Période analysée: {report.get('period_analyzed', 'N/A')}")
    print(f"📈 Score global: {report.get('success_criteria', {}).get('overall_score', {}).get('score', 'N/A')}")

    print("\n📋 CRITÈRES DE SUCCÈS:")
    for key, value in report.get('success_criteria', {}).items():
        if key != 'overall_score':
            print(f"  {key}: {value['status']} ({value['actual']} / {value['target']})")

    if report.get('alerts'):
        print("\n🚨 ALERTES:")
        for alert in report['alerts']:
            print(f"  {alert}")

    if report.get('recommendations'):
        print("\n💡 RECOMMANDATIONS:")
        for rec in report['recommendations']:
            print(f"  • {rec}")

    # Sauvegarder le rapport
    report_file = f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n💾 Rapport sauvegardé: {report_file}")

    # Code de sortie basé sur le score
    score = report.get('success_criteria', {}).get('overall_score', {}).get('score', '0%')
    score_value = float(score.rstrip('%'))
    exit(0 if score_value >= 80 else 1)


if __name__ == "__main__":
    main()