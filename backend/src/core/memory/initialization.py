"""Memory system initialization - must be called at bot startup."""

import os
from ..logger import get_logger
from .memory_manager import MemoryManager, MemoryConfig

logger = get_logger(__name__)


def initialize_memory_system() -> None:
    """Initialize the memory system at bot startup.

    This MUST be called before any trading operations.
    Configuration is controlled via environment variables.

    Environment Variables:
        MEMORY_ENABLED: "true" or "false" (default: "true")
        MEMORY_PROVIDER: "deepmem" or "none" (default: "deepmem")
        MEMORY_DEBUG: "true" or "false" (default: "false")
        MEMORY_NAME: Instance name (default: "0xBot")
    """
    # Read config from environment
    enabled = os.getenv("MEMORY_ENABLED", "true").lower() in ("true", "1", "yes")
    provider = os.getenv("MEMORY_PROVIDER", "deepmem").lower()
    debug = os.getenv("MEMORY_DEBUG", "false").lower() in ("true", "1", "yes")
    name = os.getenv("MEMORY_NAME", "0xBot")

    # Create config
    config = MemoryConfig(
        enabled=enabled,
        provider=provider,
        debug=debug,
        name=name,
    )

    # Initialize
    try:
        MemoryManager.initialize(config)
        logger.info(f"✓ Memory system initialized: enabled={enabled}, provider={provider}, debug={debug}")
    except Exception as e:
        logger.error(f"✗ Failed to initialize memory system: {e}")
        # Create a no-op config as fallback
        fallback_config = MemoryConfig(enabled=False, provider="none")
        MemoryManager.initialize(fallback_config)
        logger.warning("Using fallback no-op memory provider")


def get_memory_status() -> dict:
    """Get current memory system status.

    Returns:
        Dict with status information
    """
    try:
        import asyncio
        health = asyncio.run(MemoryManager.health_check())
        return health
    except Exception as e:
        logger.error(f"Failed to get memory status: {e}")
        return {"status": "error", "error": str(e)}
