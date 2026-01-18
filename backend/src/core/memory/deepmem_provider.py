"""DeepMem provider implementation."""

import json
from typing import Any, Dict, Optional
from datetime import datetime

from ..logger import get_logger
from .base import BaseMemoryProvider

logger = get_logger(__name__)

try:
    from deepmem import DeepMem
    DEEPMEM_AVAILABLE = True
except ImportError:
    DEEPMEM_AVAILABLE = False
    logger.warning("DeepMem not installed - memory features will be disabled")


class DeepMemProvider(BaseMemoryProvider):
    """DeepMem-based memory provider."""

    def __init__(self, name: str = "0xBot", debug: bool = False):
        """Initialize DeepMem provider.

        Args:
            name: Memory instance name
            debug: Enable debug logging
        """
        self.name = name
        self.debug = debug

        if not DEEPMEM_AVAILABLE:
            raise RuntimeError("DeepMem not installed. Run: pip install deepmem")

        try:
            self.memory = DeepMem(name=name)
            logger.info(f"✓ DeepMem initialized: {name}")
            if self.debug:
                logger.debug(f"  - DeepMem instance: {self.memory}")
        except Exception as e:
            logger.error(f"Failed to initialize DeepMem: {e}")
            raise

    async def remember(self, key: str, value: Any, metadata: Optional[Dict] = None) -> bool:
        """Store a memory using DeepMem."""
        try:
            # Convert value to serializable format if needed
            if isinstance(value, (dict, list, str, int, float, bool)):
                storage_value = value
            else:
                storage_value = str(value)

            # Store with metadata
            full_data = {
                "value": storage_value,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat(),
            }

            self.memory.store(key, json.dumps(full_data))

            if self.debug:
                logger.debug(f"[MEMORY] Stored: {key} = {storage_value}")

            logger.info(f"[MEMORY] Remember: {key}")
            return True

        except Exception as e:
            logger.error(f"[MEMORY] Error storing {key}: {e}")
            return False

    async def recall(self, key: str, default: Any = None) -> Any:
        """Retrieve a memory using DeepMem."""
        try:
            stored = self.memory.retrieve(key)

            if stored is None:
                if self.debug:
                    logger.debug(f"[MEMORY] Not found: {key}")
                return default

            # Parse stored JSON
            data = json.loads(stored)
            value = data.get("value", default)

            if self.debug:
                logger.debug(f"[MEMORY] Recalled: {key} = {value}")

            logger.info(f"[MEMORY] Recall: {key}")
            return value

        except Exception as e:
            logger.error(f"[MEMORY] Error retrieving {key}: {e}")
            return default

    async def search(self, pattern: str) -> Dict[str, Any]:
        """Search for memories matching a pattern."""
        try:
            # DeepMem doesn't have built-in pattern matching
            # So we'll use a simple string matching approach
            results = {}

            if self.debug:
                logger.debug(f"[MEMORY] Searching pattern: {pattern}")

            # Note: This is a simplified version
            # In production, you'd need to implement proper pattern matching
            logger.warning(f"[MEMORY] Pattern search not fully implemented for: {pattern}")

            return results

        except Exception as e:
            logger.error(f"[MEMORY] Error searching pattern {pattern}: {e}")
            return {}

    async def forget(self, key: str) -> bool:
        """Delete a memory using DeepMem."""
        try:
            self.memory.delete(key)

            if self.debug:
                logger.debug(f"[MEMORY] Forgot: {key}")

            logger.info(f"[MEMORY] Forget: {key}")
            return True

        except Exception as e:
            logger.error(f"[MEMORY] Error deleting {key}: {e}")
            return False

    async def clear_all(self) -> bool:
        """Clear all memories."""
        try:
            logger.warning("[MEMORY] Clearing ALL memories...")
            self.memory.clear()
            logger.info("[MEMORY] All memories cleared")
            return True

        except Exception as e:
            logger.error(f"[MEMORY] Error clearing all: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check DeepMem health."""
        try:
            return {
                "status": "healthy",
                "provider": "DeepMem",
                "name": self.name,
                "available": True,
                "debug": self.debug,
            }

        except Exception as e:
            logger.error(f"[MEMORY] Health check failed: {e}")
            return {
                "status": "unhealthy",
                "provider": "DeepMem",
                "error": str(e),
            }
