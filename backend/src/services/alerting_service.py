"""Service d'alertes pour le bot de trading."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Callable
from decimal import Decimal

from ..core.logger import get_logger


class AlertRule:
    """Règle d'alerte."""
    def __init__(self, name: str, condition: Callable, threshold: Any, message: str):
        self.name = name
        self.condition = condition
        self.threshold = threshold
        self.message = message
        self.last_triggered = None
        self.cooldown_minutes = 60  # Éviter les spam d'alertes
    
    def should_trigger(self, value: Any) -> bool:
        """Détermine si l'alerte doit être déclenchée."""
        if self.condition(value, self.threshold):
            # Vérifier le cooldown
            if (self.last_triggered and 
                datetime.utcnow() - self.last_triggered < timedelta(minutes=self.cooldown_minutes)):
                return False
            return True
        return False


class AlertingService:
    """Service de gestion des alertes."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.rules: List[AlertRule] = []
        self.alert_history = []
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Configure les règles d'alerte par défaut."""
        # Règle de perte importante
        self.add_rule(AlertRule(
            "large_loss",
            lambda value, threshold: value < 0 and abs(value) > threshold,
            Decimal("500"),
            "Large loss detected: ${value}"
        ))
        
        # Règle de temps de cycle élevé
        self.add_rule(AlertRule(
            "slow_cycle",
            lambda value, threshold: value > threshold,
            600,  # 10 minutes
            "Slow trading cycle detected: {value}s"
        ))
        
        # Règle d'erreur de trading
        self.add_rule(AlertRule(
            "trading_error",
            lambda value, threshold: value > threshold,
            5,
            "Multiple trading errors: {value} errors"
        ))
    
    def add_rule(self, rule: AlertRule):
        """Ajoute une règle d'alerte."""
        self.rules.append(rule)
        self.logger.info(f"Alert rule added: {rule.name}")
    
    async def check_conditions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Vérifie toutes les conditions d'alerte."""
        triggered_alerts = []
        
        for rule in self.rules:
            value = context.get(rule.name)
            if value is not None and rule.should_trigger(value):
                alert = {
                    "name": rule.name,
                    "message": rule.message.format(value=value),
                    "timestamp": datetime.utcnow().isoformat(),
                    "severity": "high" if "loss" in rule.name else "medium"
                }
                
                triggered_alerts.append(alert)
                rule.last_triggered = datetime.utcnow()
                self.alert_history.append(alert)
                
                # Logger l'alerte
                self.logger.warning(f"🚨 ALERT: {alert['message']}")
        
        return triggered_alerts
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Récupère les alertes récentes."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [
            alert for alert in self.alert_history
            if datetime.fromisoformat(alert["timestamp"]) > cutoff
        ]
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'alertes."""
        recent_alerts = self.get_recent_alerts(24)
        return {
            "total_alerts_24h": len(recent_alerts),
            "rules_count": len(self.rules),
            "last_alert": recent_alerts[-1]["timestamp"] if recent_alerts else None
        }


# Instance globale du service d'alertes
alerting_service = AlertingService()
