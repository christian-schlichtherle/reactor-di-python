"""Module decorator for dependency injection.

This decorator implements dependency injection by automatically creating
factory methods for annotated attributes. It uses greedy behavior,
raising errors for attributes that cannot be satisfied.
"""

from __future__ import annotations

from functools import cached_property
from typing import Any, Callable, Type, Union, get_type_hints

from .caching import CachingStrategy
from .type_utils import (
    SETUP_DEPENDENCIES_ATTR,
    is_primitive_type,
    pure_hasattr,
)


def _module_getattr(self: Any, name: str) -> Any:
    """Fallback __getattr__ for deferred dependency setup.

    Installed on component classes by the module factory.  Only called
    when normal attribute lookup fails (i.e. the attribute is not in the
    instance dict and not a descriptor on the class).  Triggers the
    deferred setup function which resolves all dependencies at once.
    """
    setup_func = self.__dict__.pop(SETUP_DEPENDENCIES_ATTR, None)
    if setup_func:
        setup_func()
        return getattr(self, name)
    raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


_module_getattr._reactor_di = True  # type: ignore[attr-defined]


def _create_factory_method(
    attr_type: Type[Any], caching_strategy: CachingStrategy
) -> Union[property, cached_property[Any]]:
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

        # For each dependency needed by the instance, build a mapping
        # from dep name to module attribute using naming conventions
        for dep_name in get_type_hints(attr_type):
            # Direct match: dependency name matches module_instance attribute
            if pure_hasattr(module_instance, dep_name):
                dependency_map[dep_name] = dep_name
            # Convention match: _config maps to config in module_instance
            elif dep_name.startswith("_"):
                alt_name = dep_name[1:]  # Remove leading underscore
                if pure_hasattr(module_instance, alt_name):
                    dependency_map[dep_name] = alt_name

        if dependency_map:

            def setup_dependencies() -> None:
                for dep_name, parent_attr in dependency_map.items():
                    dep_value = getattr(module_instance, parent_attr)
                    setattr(instance, dep_name, dep_value)

            # Store setup function for _DeferredProperty and __getattr__
            instance.__dict__[SETUP_DEPENDENCIES_ATTR] = setup_dependencies

            # Install __getattr__ on the class so that non-descriptor
            # dependencies (those not handled by _DeferredProperty) trigger
            # setup on first access.  Unlike __getattribute__, __getattr__
            # is only called when normal lookup fails, so it doesn't
            # interfere with existing attributes or descriptors.
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
    if caching_strategy == CachingStrategy.DISABLED:
        return property(factory)
    raise ValueError(f"Unsupported caching strategy: {caching_strategy}")


def _apply_module_decorator(
    class_type: Type[Any], caching_strategy: CachingStrategy
) -> Type[Any]:
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
    class_or_strategy: Union[Type[Any], CachingStrategy, None] = None, /
) -> Union[Type[Any], Callable[[Type[Any]], Type[Any]]]:
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
