"""Service locator pattern for dependency injection.

This module provides a centralized service registry for managing application-wide
dependencies with lazy instantiation and flexible resolution patterns.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from mcp_server.state import ApplicationState
    from search.config import SearchConfig


class ServiceLocator:
    """Centralized service registry for dependency resolution.

    The Service Locator pattern provides a less invasive approach to dependency
    injection compared to constructor injection, allowing flexible dependency
    resolution while supporting both direct access and service location patterns.

    Features:
    - Singleton pattern for global access
    - Lazy instantiation via factory registration
    - Testability through reset() method
    - Type-safe convenience methods for common services

    Example:
        >>> # Registration (typically at app startup)
        >>> locator = ServiceLocator.instance()
        >>> locator.register("state", ApplicationState())
        >>>
        >>> # Access
        >>> state = locator.get_state()
        >>>
        >>> # Testing
        >>> ServiceLocator.reset()  # Clean slate for tests
    """

    _instance: "ServiceLocator" | None = None

    def __init__(self) -> None:
        """Initialize empty service registry.

        Note: Use ServiceLocator.instance() instead of direct construction.
        """
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Callable[[], Any]] = {}

    @classmethod
    def instance(cls) -> "ServiceLocator":
        """Get the singleton ServiceLocator instance.

        Returns:
            The global ServiceLocator instance, creating it if needed.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance for testing.

        This should be called in test fixtures to ensure clean state between tests.
        """
        cls._instance = None

    def register(self, name: str, service: Any) -> None:
        """Register a service instance.

        Args:
            name: Service identifier (e.g., "state", "config")
            service: The service instance to register
        """
        self._services[name] = service

    def register_factory(self, name: str, factory: Callable[[], Any]) -> None:
        """Register a factory for lazy service instantiation.

        The factory will be called on first access to create the service instance.

        Args:
            name: Service identifier
            factory: Callable that returns the service instance
        """
        self._factories[name] = factory

    def invalidate(self, name: str) -> bool:
        """Invalidate a cached service to force re-creation on next access.

        Useful when a service's underlying state has changed and needs to be
        reloaded. For example, invalidating the config service when the config
        file has been modified.

        Args:
            name: Service identifier to invalidate

        Returns:
            True if service was cached and removed, False otherwise

        Example:
            >>> locator = ServiceLocator.instance()
            >>> locator.invalidate("config")  # Force config reload on next access
            True
        """
        if name in self._services:
            del self._services[name]
            return True
        return False

    def get(self, name: str) -> Any:
        """Get a service by name, lazily creating it if a factory is registered.

        Args:
            name: Service identifier

        Returns:
            The service instance, or None if not found

        Note:
            If a factory is registered for this service and it hasn't been
            instantiated yet, the factory will be called to create the instance.
        """
        if name not in self._services and name in self._factories:
            self._services[name] = self._factories[name]()
        return self._services.get(name)

    # Typed convenience methods for common services

    def get_state(self) -> "ApplicationState":
        """Get the ApplicationState service.

        Returns:
            The registered ApplicationState instance

        Raises:
            TypeError: If the service is not registered or not an ApplicationState
        """
        state = self.get("state")
        if state is None:
            # Auto-create if not registered
            from mcp_server.state import get_state as _get_legacy_state

            state = _get_legacy_state()
            self.register("state", state)
        return state

    def get_config(self) -> "SearchConfig":
        """Get the SearchConfig service.

        Returns:
            The registered SearchConfig instance

        Raises:
            TypeError: If the service is not registered or not a SearchConfig
        """
        config = self.get("config")
        if config is None:
            # Auto-create if not registered
            from search.config import get_search_config

            config = get_search_config()
            self.register("config", config)
        return config


# Convenience wrappers for common access patterns
def get_state() -> "ApplicationState":
    """Get ApplicationState via ServiceLocator (backward-compatible wrapper).

    This function maintains compatibility with existing code that calls get_state()
    directly, while transitioning to the ServiceLocator pattern internally.

    Returns:
        The ApplicationState instance from ServiceLocator
    """
    return ServiceLocator.instance().get_state()


def get_config() -> "SearchConfig":
    """Get SearchConfig via ServiceLocator (backward-compatible wrapper).

    Returns:
        The SearchConfig instance from ServiceLocator
    """
    return ServiceLocator.instance().get_config()
