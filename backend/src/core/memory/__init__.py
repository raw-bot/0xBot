"""Memory system for trading bot - DeepMem integration.

This module provides a switchable memory system for the trading bot.
Can be toggled on/off via configuration without code changes.

IMPORTANT: Call initialize_memory_system() at bot startup!
"""

from .base import BaseMemoryProvider
from .memory_manager import MemoryManager, MemoryConfig
from .initialization import initialize_memory_system, get_memory_status

__all__ = [
    "BaseMemoryProvider",
    "MemoryManager",
    "MemoryConfig",
    "initialize_memory_system",
    "get_memory_status",
]
