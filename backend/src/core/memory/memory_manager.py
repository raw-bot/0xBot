"""Central memory manager - switchable on/off."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..logger import get_logger
from .base import BaseMemoryProvider
from .deepmem_provider import DeepMemProvider, DEEPMEM_AVAILABLE

logger = get_logger(__name__)


@dataclass
class MemoryConfig:
    """Configuration for memory system."""

    enabled: bool = True  # Master switch
    provider: str = "deepmem"  # "deepmem" or "none"
    debug: bool = False  # Enable debug logging
    name: str = "0xBot"  # Memory instance name


class DummyMemoryProvider(BaseMemoryProvider):
    """No-op memory provider when memory is disabled."""

    async def remember(self, key: str, value: Any, metadata: Optional[dict[str, Any]] = None) -> bool:
        return True

    async def recall(self, key: str, default: Any = None) -> Any:
        return default

    async def search(self, pattern: str) -> dict[str, Any]:
        return {}

    async def forget(self, key: str) -> bool:
        return True

    async def clear_all(self) -> bool:
        return True

    async def health_check(self) -> dict[str, Any]:
        return {"status": "disabled", "provider": "none"}


class MemoryManager:
    """Central memory manager - handles all memory operations."""

    _instance: Optional["MemoryManager"] = None  # Singleton
    _config: Optional[MemoryConfig] = None
    _provider: Optional[BaseMemoryProvider] = None
    _initialized: bool = False

    def __new__(cls) -> "MemoryManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    @classmethod
    def initialize(cls, config: Optional[MemoryConfig] = None) -> "MemoryManager":
        """Initialize the memory manager.

        Args:
            config: MemoryConfig instance

        Returns:
            MemoryManager instance
        """
        instance = cls()

        if instance._initialized:
            return instance

        config = config or MemoryConfig()
        cls._config = config

        logger.info(f"Initializing MemoryManager: enabled={config.enabled}, provider={config.provider}")

        if not config.enabled:
            logger.warning("⚠️  Memory system is DISABLED (dummy provider)")
            cls._provider = DummyMemoryProvider()
            instance._initialized = True
            return instance

        try:
            if config.provider == "deepmem":
                if not DEEPMEM_AVAILABLE:
                    logger.error("DeepMem not available - switching to dummy provider")
                    cls._provider = DummyMemoryProvider()
                else:
                    cls._provider = DeepMemProvider(name=config.name, debug=config.debug)
                    logger.info("✓ DeepMem provider initialized")

            else:
                logger.warning(f"Unknown provider: {config.provider} - using dummy")
                cls._provider = DummyMemoryProvider()

        except Exception as e:
            logger.error(f"Failed to initialize memory provider: {e} - using dummy")
            cls._provider = DummyMemoryProvider()

        instance._initialized = True
        return instance

    @classmethod
    def get_provider(cls) -> BaseMemoryProvider:
        """Get the memory provider."""
        if cls._provider is None:
            cls.initialize()
        return cls._provider  # type: ignore[return-value]

    @classmethod
    async def remember(
        cls, key: str, value: Any, metadata: Optional[dict[str, Any]] = None
    ) -> bool:
        """Remember something.

        Args:
            key: Memory key
            value: Value to store
            metadata: Optional metadata

        Returns:
            True if stored
        """
        provider = cls.get_provider()
        return await provider.remember(key, value, metadata)

    @classmethod
    async def recall(cls, key: str, default: Any = None) -> Any:
        """Recall something.

        Args:
            key: Memory key
            default: Default value if not found

        Returns:
            Stored value or default
        """
        provider = cls.get_provider()
        return await provider.recall(key, default)

    @classmethod
    async def search(cls, pattern: str) -> dict[str, Any]:
        """Search for memories.

        Args:
            pattern: Search pattern

        Returns:
            Dict of matching memories
        """
        provider = cls.get_provider()
        return await provider.search(pattern)

    @classmethod
    async def forget(cls, key: str) -> bool:
        """Forget something.

        Args:
            key: Memory key

        Returns:
            True if forgotten
        """
        provider = cls.get_provider()
        return await provider.forget(key)

    @classmethod
    async def clear_all(cls) -> bool:
        """Clear all memories."""
        provider = cls.get_provider()
        return await provider.clear_all()

    @classmethod
    async def health_check(cls) -> dict[str, Any]:
        """Check memory system health."""
        provider = cls.get_provider()
        health = await provider.health_check()

        if cls._config:
            health["config"] = {
                "enabled": cls._config.enabled,
                "provider": cls._config.provider,
                "debug": cls._config.debug,
            }

        return health

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if memory system is enabled."""
        if cls._config is None:
            cls.initialize()
        return cls._config.enabled if cls._config else False

    @classmethod
    def switch_on(cls) -> None:
        """Enable memory system."""
        if cls._config:
            cls._config.enabled = True
            # Switch to real provider if available
            if cls._config.provider == "deepmem":
                if DEEPMEM_AVAILABLE:
                    cls._provider = DeepMemProvider(name=cls._config.name, debug=cls._config.debug)
                else:
                    logger.error("DeepMem not available - cannot enable")
                    return
            logger.info("✓ Memory system ENABLED")

    @classmethod
    def switch_off(cls) -> None:
        """Disable memory system."""
        if cls._config:
            cls._config.enabled = False
            # Switch to dummy provider (no-op)
            cls._provider = DummyMemoryProvider()
            logger.warning("⚠️  Memory system DISABLED (using dummy provider)")

    @classmethod
    def debug_on(cls) -> None:
        """Enable debug logging."""
        if cls._config:
            cls._config.debug = True
            logger.info("✓ Memory debug logging ENABLED")

    @classmethod
    def debug_off(cls) -> None:
        """Disable debug logging."""
        if cls._config:
            cls._config.debug = False
            logger.info("✓ Memory debug logging DISABLED")
