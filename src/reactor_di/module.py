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

        Instantiates the dependency and sets up lazy resolution for its
        sub-dependencies through a deferred loading mechanism.
        """

        # Create the instance without trying to resolve any dependencies.
        # The dependencies will be resolved lazily when accessed.
        instance = attr_type()
        dependency_map = {}

        # For each dependency needed by the instance
        for dep_name in get_type_hints(attr_type):
            # Direct match: dependency name matches module_instance attribute
            if pure_hasattr(module_instance, dep_name):
                dependency_map[dep_name] = dep_name
            # Convention match: _config maps to config in module_instance
            elif dep_name.startswith("_"):
                alt_name = dep_name[1:]  # Remove leading underscore
                if pure_hasattr(module_instance, alt_name):
                    dependency_map[dep_name] = alt_name

        # Store the dependency mapping for later use
        if dependency_map:
            # Set up the dependencies that are base references (not forwarded)
            # These are dependencies that would be injected directly
            # We need to defer this until after the instance is fully created
            # to avoid circular dependencies
            def setup_dependencies() -> None:
                for dep_name, parent_attr in dependency_map.items():
                    # Resolve the dependency from the parent
                    dep_value = getattr(module_instance, parent_attr)
                    setattr(instance, dep_name, dep_value)

            # Store the setup function to be called later
            instance.__dict__[SETUP_DEPENDENCIES_ATTR] = setup_dependencies

            # Also set up __getattribute__ to call setup when dependencies are accessed
            original_getattribute = instance.__class__.__getattribute__

            def patched_getattribute(self: Any, name: str) -> Any:
                # Call setup if it exists and we're accessing a dependency
                if name in dependency_map:
                    setup_func = self.__dict__.get(SETUP_DEPENDENCIES_ATTR)
                    if setup_func:
                        setup_func()
                        del self.__dict__[SETUP_DEPENDENCIES_ATTR]

                return original_getattribute(self, name)

            instance.__class__.__getattribute__ = patched_getattribute

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
