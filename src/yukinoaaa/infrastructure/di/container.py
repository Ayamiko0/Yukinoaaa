"""Lightweight Dependency Injection Container."""

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class Container:
    """Simple, type-safe dependency injection container."""

    def __init__(self) -> None:
        """Initialize registries for singletons and factories."""
        self._singletons: dict[type[Any] | str, Any] = {}
        self._factories: dict[type[Any] | str, Callable[[Container], Any]] = {}

    def register_singleton(self, key: type[T] | str, instance: T) -> None:
        """Register a pre-constructed singleton object."""
        self._singletons[key] = instance

    def register_factory(self, key: type[T] | str, factory: Callable[["Container"], T]) -> None:
        """Register a factory function for lazy instantiation."""
        self._factories[key] = factory

    def resolve(self, key: type[T] | str) -> T:
        """Resolve an instance by type or string key."""
        if key in self._singletons:
            return self._singletons[key]  # type: ignore[no-any-return]

        if key in self._factories:
            instance = self._factories[key](self)
            return instance  # type: ignore[no-any-return]

        raise KeyError(f"Dependency not registered in DI Container: {key}")

    def clear(self) -> None:
        """Clear all registered dependencies (for testing)."""
        self._singletons.clear()
        self._factories.clear()
