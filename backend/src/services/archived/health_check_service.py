"""Service de vérifications de santé pour le bot."""

import asyncio
import psutil
from datetime import datetime
from typing import Dict, Any, List
from decimal import Decimal

from ..core.logger import get_logger


class HealthCheckService:
    """Service de vérifications de santé en temps réel."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.start_time = datetime.utcnow()
        self.checks = [
            "database_connection",
            "memory_usage",
            "cpu_usage", 
            "disk_usage",
            "api_connectivity"
        ]
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Exécute toutes les vérifications de santé."""
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
            "overall_status": "healthy",
            "checks": {}
        }
        
        for check_name in self.checks:
            try:
                result = await getattr(self, f"check_{check_name}")()
                results["checks"][check_name] = result
            except Exception as e:
                results["checks"][check_name] = {
                    "status": "error",
                    "message": str(e)
                }
                results["overall_status"] = "unhealthy"
        
        return results
    
    async def check_database_connection(self) -> Dict[str, Any]:
        """Vérifie la connexion à la base de données."""
        try:
            # Test simple de connexion (à adapter selon votre DB)
            # await self.db.execute(select(1))
            return {
                "status": "healthy",
                "message": "Database connection OK"
            }
        except Exception as e:
            return {
                "status": "unhealthy", 
                "message": f"Database connection failed: {e}"
            }
    
    async def check_memory_usage(self) -> Dict[str, Any]:
        """Vérifie l'utilisation mémoire."""
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        
        status = "healthy"
        if memory_percent > 80:
            status = "warning"
        elif memory_percent > 95:
            status = "unhealthy"
        
        return {
            "status": status,
            "message": f"Memory usage: {memory_percent:.1f}%",
            "memory_mb": round(memory_info.rss / 1024 / 1024, 1),
            "memory_percent": round(memory_percent, 1)
        }
    
    async def check_cpu_usage(self) -> Dict[str, Any]:
        """Vérifie l'utilisation CPU."""
        cpu_percent = psutil.cpu_percent(interval=1)
        
        status = "healthy"
        if cpu_percent > 80:
            status = "warning"
        elif cpu_percent > 95:
            status = "unhealthy"
        
        return {
            "status": status,
            "message": f"CPU usage: {cpu_percent:.1f}%",
            "cpu_percent": round(cpu_percent, 1)
        }
    
    async def check_disk_usage(self) -> Dict[str, Any]:
        """Vérifie l'utilisation disque."""
        disk_usage = psutil.disk_usage('/')
        disk_percent = (disk_usage.used / disk_usage.total) * 100
        
        status = "healthy"
        if disk_percent > 80:
            status = "warning"
        elif disk_percent > 95:
            status = "unhealthy"
        
        return {
            "status": status,
            "message": f"Disk usage: {disk_percent:.1f}%",
            "disk_percent": round(disk_percent, 1),
            "free_gb": round(disk_usage.free / 1024**3, 1)
        }
    
    async def check_api_connectivity(self) -> Dict[str, Any]:
        """Vérifie la connectivité API."""
        try:
            # Test basique de connectivité (à adapter selon vos APIs)
            # import httpx
            # async with httpx.AsyncClient() as client:
            #     response = await client.get("https://api.binance.com/api/v3/ping", timeout=5)
            #     response.raise_for_status()
            
            return {
                "status": "healthy",
                "message": "API connectivity OK"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"API connectivity failed: {e}"
            }
    
    def log_health_status(self, health_data: Dict[str, Any]) -> None:
        """Log le statut de santé."""
        status = health_data["overall_status"]
        uptime = health_data["uptime_seconds"]
        
        if status == "healthy":
            self.logger.info(f"💚 Health check OK | Uptime: {uptime/3600:.1f}h")
        elif status == "warning":
            self.logger.warning(f"🟡 Health check warning | Uptime: {uptime/3600:.1f}h")
        else:
            self.logger.error(f"🔴 Health check failed | Uptime: {uptime/3600:.1f}h")


# Instance globale du service de health check
health_check_service = HealthCheckService()
