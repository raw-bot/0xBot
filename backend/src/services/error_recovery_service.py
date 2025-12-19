"""Service de récupération automatique après erreurs."""

import asyncio
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, Optional
from enum import Enum

from ..core.logger import get_logger


class ErrorType(Enum):
    """Types d'erreurs."""
    NETWORK = "network"
    DATABASE = "database" 
    API_RATE_LIMIT = "api_rate_limit"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


class RecoveryStrategy:
    """Stratégie de récupération."""
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor


class ErrorRecoveryService:
    """Service de récupération automatique d'erreurs."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.recovery_strategies = {
            ErrorType.NETWORK: RecoveryStrategy(max_retries=5, backoff_factor=2.0),
            ErrorType.DATABASE: RecoveryStrategy(max_retries=3, backoff_factor=1.5),
            ErrorType.API_RATE_LIMIT: RecoveryStrategy(max_retries=3, backoff_factor=3.0)
        }
        self.error_counts = {}
        self.last_errors = {}
    
    def identify_error_type(self, exception: Exception) -> ErrorType:
        """Identifie le type d'erreur."""
        error_msg = str(exception).lower()
        
        if any(word in error_msg for word in ['connection', 'timeout', 'network']):
            return ErrorType.NETWORK
        elif any(word in error_msg for word in ['database', 'sql', 'query']):
            return ErrorType.DATABASE
        elif any(word in error_msg for word in ['rate limit', 'quota', 'too many requests']):
            return ErrorType.API_RATE_LIMIT
        elif any(word in error_msg for word in ['validation', 'invalid', 'value error']):
            return ErrorType.VALIDATION
        else:
            return ErrorType.UNKNOWN
    
    async def execute_with_recovery(self, func: Callable, *args, **kwargs) -> Any:
        """Exécute une fonction avec récupération automatique."""
        error_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
        error_type = None
        last_exception = None
        
        for attempt in range(1, 6):  # Maximum 5 tentatives
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Succès - réinitialiser le compteur d'erreurs
                if error_key in self.error_counts:
                    del self.error_counts[error_key]
                
                return result
                
            except Exception as e:
                last_exception = e
                error_type = self.identify_error_type(e)
                
                self.logger.warning(f"Attempt {attempt} failed for {func.__name__}: {e}")
                
                # Identifier la stratégie de récupération
                strategy = self.recovery_strategies.get(error_type, RecoveryStrategy())
                
                if attempt >= strategy.max_retries:
                    self.logger.error(f"All recovery attempts failed for {func.__name__}")
                    break
                
                # Calculer le délai de backoff
                delay = strategy.backoff_factor ** (attempt - 1)
                self.logger.info(f"Retrying in {delay}s (attempt {attempt + 1})")
                await asyncio.sleep(delay)
                
                # Mettre à jour les compteurs
                self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
                self.last_errors[error_key] = {
                    "timestamp": datetime.utcnow(),
                    "error": str(e),
                    "type": error_type.value,
                    "attempt": attempt
                }
        
        # Toutes les tentatives ont échoué
        self.logger.error(f"Permanent failure for {func.__name__}: {last_exception}")
        raise last_exception
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques d'erreurs."""
        return {
            "total_errors": sum(self.error_counts.values()),
            "unique_errors": len(self.error_counts),
            "most_common_errors": sorted(
                self.error_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5],
            "recent_errors": [
                {
                    "key": key,
                    "count": count,
                    "last_occurrence": info["timestamp"].isoformat()
                }
                for key, count in self.error_counts.items()
            ]
        }


# Instance globale du service de récupération
error_recovery_service = ErrorRecoveryService()
