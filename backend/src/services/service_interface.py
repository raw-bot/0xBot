"""Interface commune pour tous les services."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class TradingServiceInterface(ABC):
    """Interface commune pour tous les services de trading."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialise le service."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Ferme proprement le service."""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Retourne l'état du service."""
        pass


class ConfigurableService(ABC):
    """Mixin pour services avec configuration."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Récupère une valeur de configuration."""
        return self.config.get(key, default)
