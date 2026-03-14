"""Module decorator for dependency injection.

This decorator implements dependency injection by automatically creating
factory methods for annotated attributes. It uses greedy behavior,
raising errors for attributes that cannot be satisfied.
"""

from __future__ import annotations

import threading
from functools import cached_property
from typing import Any, Callable, get_type_hints

from .caching import CachingStrategy, thread_safe_cached_property
from .type_utils import (
    DEPENDENCY_MAP_ATTR,
    MODULE_INSTANCE_ATTR,
    REACTOR_DI_LOCK_ATTR,
    is_primitive_type,
    pure_hasattr,
)


def _module_getattr(self: Any, name: str) -> Any:
    """Fallback __getattr__ for lazy per-attribute dependency resolution.

    Installed on component classes by the module factory.  Only called
    when normal attribute lookup fails (i.e. the attribute is not in the
    instance dict and not a descriptor on the class).  Resolves individual
    dependencies lazily from the module instance, so that accessing one
    dependency does not trigger resolution of unrelated dependencies.
    """
    dep_map = self.__dict__.get(DEPENDENCY_MAP_ATTR)
    if dep_map is not None and name in dep_map:
        lock = self.__dict__.get(REACTOR_DI_LOCK_ATTR)
        if lock is not None:
            return _resolve_dep_locked(self, name, dep_map, lock)
        return _resolve_dep(self, name, dep_map)
    raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


_module_getattr._reactor_di = True  # type: ignore[attr-defined]


def _resolve_dep(self: Any, name: str, dep_map: dict[str, str]) -> Any:
    """Resolve a single dependency from the module instance (no locking)."""
    module_ref = self.__dict__[MODULE_INSTANCE_ATTR]
    parent_attr = dep_map[name]
    dep_value = getattr(module_ref, parent_attr)
    setattr(self, name, dep_value)
    del dep_map[name]
    if not dep_map:
        del self.__dict__[DEPENDENCY_MAP_ATTR]
        del self.__dict__[MODULE_INSTANCE_ATTR]
    return dep_value


def _resolve_dep_locked(
    self: Any, name: str, dep_map: dict[str, str], lock: threading.Lock
) -> Any:
    """Resolve a single dependency under a lock for thread safety."""
    with lock:
        # Double-check: another thread may have resolved it already
        if name in self.__dict__:
            return self.__dict__[name]
        if name not in dep_map:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )
        return _resolve_dep(self, name, dep_map)


def _create_factory_method(
    attr_type: type[Any], caching_strategy: CachingStrategy
) -> property | cached_property[Any] | thread_safe_cached_property:
    """Create a factory method for a dependency.

    Generates a property that lazily instantiates dependencies. The factory
    handles dependency injection by mapping child class dependencies to
    parent class attributes through naming conventions.

    Args:
        attr_type: Type of the dependency to create.
        caching_strategy: Caching strategy to use.

    Returns:
        A property or cached_property that creates the dependency.
    """

    def factory(module_instance: Any) -> Any:
        """Factory function that creates the dependency.

        Instantiates the dependency and sets up deferred resolution for its
        sub-dependencies from the module instance.
        """

        instance = attr_type()
        dependency_map = {}

        # Get dependency names, handling TYPE_CHECKING forward references.
        # When a component uses `if TYPE_CHECKING:` imports (common for
        # avoiding circular imports), get_type_hints() fails with NameError
        # because the referenced type isn't available at runtime.  We only
        # need annotation *names* here, so falling back to raw __annotations__
        # from the MRO is safe.
        try:
            dep_names = get_type_hints(attr_type)
        except (NameError, AttributeError, TypeError):
            dep_names = {}
            for klass in reversed(attr_type.__mro__):
                if klass is not object:
                    dep_names.update(getattr(klass, "__annotations__", {}))

        # For each dependency needed by the instance, build a mapping
        # from dep name to module attribute using naming conventions
        for dep_name in dep_names:
            # Direct match: dependency name matches module_instance attribute
            if pure_hasattr(module_instance, dep_name):
                dependency_map[dep_name] = dep_name
            # Convention match: _config maps to config in module_instance
            elif dep_name.startswith("_"):
                alt_name = dep_name[1:]  # Remove leading underscore
                if pure_hasattr(module_instance, alt_name):
                    dependency_map[dep_name] = alt_name

        if dependency_map:
            # Store dependency map and module reference for lazy resolution.
            # Each dependency is resolved individually when first accessed,
            # avoiding eager resolution of all dependencies at once.
            instance.__dict__[DEPENDENCY_MAP_ATTR] = dict(dependency_map)
            instance.__dict__[MODULE_INSTANCE_ATTR] = module_instance

            # For THREAD_SAFE modules, store a lock on the instance so
            # _module_getattr can synchronize lazy dependency resolution.
            if caching_strategy == CachingStrategy.THREAD_SAFE:
                instance.__dict__[REACTOR_DI_LOCK_ATTR] = threading.Lock()

            # Install __getattr__ on the class so that non-descriptor
            # dependencies (those not handled by _DeferredProperty) trigger
            # lazy resolution on first access.  Unlike __getattribute__,
            # __getattr__ is only called when normal lookup fails, so it
            # doesn't interfere with existing attributes or descriptors.
            if not getattr(
                attr_type.__dict__.get("__getattr__"),
                "_reactor_di",
                False,
            ):
                attr_type.__getattr__ = _module_getattr

        return instance

    # Apply caching strategy
    if caching_strategy == CachingStrategy.NOT_THREAD_SAFE:
        return cached_property(factory)
    if caching_strategy == CachingStrategy.THREAD_SAFE:
        return thread_safe_cached_property(factory)
    if caching_strategy == CachingStrategy.DISABLED:
        return property(factory)
    raise ValueError(f"Unsupported caching strategy: {caching_strategy}")


def _apply_module_decorator(
    class_type: type[Any], caching_strategy: CachingStrategy
) -> type[Any]:
    """Apply the module decorator to a class.

    Processes all type-annotated attributes and creates factory methods for
    instantiable types. Skips primitive types and raises errors for
    unsatisfiable dependencies.

    Args:
        class_type: The class to decorate.
        caching_strategy: The caching strategy to use.

    Returns:
        The decorated class with factory methods.

    Raises:
        TypeError: If any dependency cannot be satisfied (greedy behavior).
    """
    # Process each type-annotated attribute
    for attr_name, attr_type in get_type_hints(class_type).items():
        if hasattr(class_type, attr_name):
            continue

        if isinstance(attr_type, str):
            raise TypeError(
                f"Cannot instantiate dependencies of unchecked types: {attr_name}"
            )

        # Skip primitive types (handled by other decorators)
        if is_primitive_type(attr_type):
            continue

        # Validate that we can create this type (greedy behavior)
        if not hasattr(attr_type, "__init__"):
            raise TypeError(
                f"Cannot instantiate dependencies without a (potentially implicit) constructor: {attr_name}: {attr_type}"
            )

        # Create the factory method
        factory_method = _create_factory_method(attr_type, caching_strategy)
        setattr(class_type, attr_name, factory_method)

        # Call __set_name__ if it exists (required for cached_property)
        if hasattr(factory_method, "__set_name__"):
            factory_method.__set_name__(class_type, attr_name)

    return class_type


def module(
    class_or_strategy: type[Any] | CachingStrategy | None = None, /
) -> type[Any] | Callable[[type[Any]], type[Any]]:
    """Module decorator for dependency injection.

    This decorator automatically creates factory methods for annotated
    attributes, implementing dependency injection with configurable caching.
    It uses greedy behaviour, raising errors for unsatisfied dependencies.

    Args:
        class_or_strategy: Either a class to decorate directly, or a caching strategy.

    Returns:
        Either a decorated class or a decorator function.

    Raises:
        TypeError: If any dependency cannot be satisfied (greedy behavior).

    Example:
        >>> @module
        ... class AppModule:
        ...     config: Config
        ...     service: MyService

        >>> @module(CachingStrategy.NOT_THREAD_SAFE)
        ... class AppModule:
        ...     config: Config
        ...     service: MyService
    """
    # Handle different call patterns
    if class_or_strategy is None:
        # @module() - empty parentheses
        return lambda class_type: _apply_module_decorator(
            class_type, CachingStrategy.DISABLED
        )
    if isinstance(class_or_strategy, CachingStrategy):
        # @module(CachingStrategy.NOT_THREAD_SAFE) - with strategy
        return lambda class_type: _apply_module_decorator(class_type, class_or_strategy)
    # @module - no parentheses, direct class decoration
    return _apply_module_decorator(class_or_strategy, CachingStrategy.DISABLED)
