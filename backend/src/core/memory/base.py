"""Base memory provider interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseMemoryProvider(ABC):
    """Abstract base class for memory providers."""

    @abstractmethod
    async def remember(self, key: str, value: Any, metadata: Optional[Dict] = None) -> bool:
        """Store a memory.

        Args:
            key: Memory key (e.g., "trade:BTCUSD:profitable")
            value: Memory content
            metadata: Optional metadata (symbol, timestamp, etc)

        Returns:
            True if stored successfully
        """
        pass

    @abstractmethod
    async def recall(self, key: str, default: Any = None) -> Any:
        """Retrieve a memory.

        Args:
            key: Memory key
            default: Default value if not found

        Returns:
            Stored value or default
        """
        pass

    @abstractmethod
    async def search(self, pattern: str) -> Dict[str, Any]:
        """Search for memories matching a pattern.

        Args:
            pattern: Search pattern (e.g., "trade:*" or "BTC")

        Returns:
            Dict of matching memories
        """
        pass

    @abstractmethod
    async def forget(self, key: str) -> bool:
        """Delete a memory.

        Args:
            key: Memory key

        Returns:
            True if deleted
        """
        pass

    @abstractmethod
    async def clear_all(self) -> bool:
        """Clear all memories."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check health of memory provider.

        Returns:
            Dict with health status and debug info
        """
        pass
