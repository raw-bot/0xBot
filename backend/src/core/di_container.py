"""Dependency Injection container for managing service singletons."""

import asyncio
from typing import Any, Callable, Dict, Optional, TypeVar

T = TypeVar("T")


class ServiceContainer:
    """
    Dependency Injection container for managing service instances.

    Supports both factory functions and singleton patterns.
    All services are initialized lazily on first access.
    """

    def __init__(self) -> None:
        """Initialize the service container."""
        self._services: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._startup_hooks: list[Callable] = []
        self._shutdown_hooks: list[Callable] = []

    def register(
        self,
        name: str,
        factory: Callable,
        singleton: bool = True,
        startup_hook: Optional[Callable] = None,
        shutdown_hook: Optional[Callable] = None,
    ) -> None:
        """
        Register a service factory.

        Args:
            name: Service identifier
            factory: Callable that creates/initializes the service
            singleton: If True, create once and reuse; if False, create new on each get()
            startup_hook: Optional async callable to run during container.startup()
            shutdown_hook: Optional async callable to run during container.shutdown()
        """
        self._services[name] = factory
        if startup_hook:
            self._startup_hooks.append(startup_hook)
        if shutdown_hook:
            self._shutdown_hooks.append(shutdown_hook)

    def get(self, name: str) -> Any:
        """
        Get service instance.

        If singleton, creates once and caches. Otherwise creates new instance each time.

        Args:
            name: Service identifier

        Returns:
            Service instance

        Raises:
            KeyError: If service not registered
        """
        if name not in self._services:
            raise KeyError(f"Service '{name}' not registered in container")

        factory = self._services[name]
        singleton = True  # Default to singleton for now

        if singleton:
            if name not in self._singletons:
                self._singletons[name] = factory()
            return self._singletons[name]
        else:
            return factory()

    async def get_async(self, name: str) -> Any:
        """
        Get service instance asynchronously.

        Handles both sync and async factories.

        Args:
            name: Service identifier

        Returns:
            Service instance

        Raises:
            KeyError: If service not registered
        """
        if name not in self._services:
            raise KeyError(f"Service '{name}' not registered in container")

        factory = self._services[name]
        singleton = True  # Default to singleton for now

        if singleton:
            if name not in self._singletons:
                result = factory()
                if asyncio.iscoroutine(result):
                    self._singletons[name] = await result
                else:
                    self._singletons[name] = result
            return self._singletons[name]
        else:
            result = factory()
            if asyncio.iscoroutine(result):
                return await result
            return result

    async def startup(self) -> None:
        """Initialize all registered services and run startup hooks."""
        for hook in self._startup_hooks:
            if asyncio.iscoroutinefunction(hook):
                await hook()
            else:
                hook()

    async def shutdown(self) -> None:
        """Run shutdown hooks and cleanup all services."""
        for hook in self._shutdown_hooks:
            if asyncio.iscoroutinefunction(hook):
                await hook()
            else:
                hook()
        self._singletons.clear()

    def clear(self) -> None:
        """Clear all singleton instances (for testing)."""
        self._singletons.clear()

    def is_registered(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services


# Global container instance
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """Get the global service container."""
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


def create_new_container() -> ServiceContainer:
    """Create a new container (useful for testing)."""
    return ServiceContainer()
