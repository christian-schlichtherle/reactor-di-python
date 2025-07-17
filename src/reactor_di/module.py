"""Module decorator for dependency injection.

This decorator implements dependency injection by automatically creating
factory methods for annotated attributes. It uses greedy behavior,
raising errors for attributes that cannot be satisfied.
"""

from functools import cached_property
from typing import Any, Callable, Type, Union

from .caching import CachingStrategy
from .type_utils import get_all_type_hints, needs_implementation


def _create_factory_method(
    attr_name: str, attr_type: Type[Any], caching_strategy: CachingStrategy
) -> Union[property, cached_property[Any]]:
    """Create a factory method for a dependency.

    Args:
        attr_name: Name of the attribute to create a factory for.
        attr_type: Type of the dependency to create.
        caching_strategy: Caching strategy to use.

    Returns:
        A property or cached_property that creates the dependency.
    """

    def factory(self_instance: Any) -> Any:
        """Factory function that creates the dependency."""
        # Try to create instance with dependencies
        try:
            # Get the class constructor
            if not hasattr(attr_type, "__init__"):
                raise TypeError(
                    f"Cannot instantiate {attr_type.__name__}: no constructor"
                )

            # Create the instance without trying to resolve dependencies
            # Dependencies will be resolved lazily when accessed
            instance = attr_type()

            # Set up lazy dependency resolution by setting a reference back to parent
            # This allows the created instance to access parent dependencies when needed
            if hasattr(instance, "__dict__"):
                instance.__dict__["_parent_instance"] = self_instance

                # Set up lazy dependency resolution using a deferred approach
                instance_hints = get_all_type_hints(attr_type)
                parent_hints = get_all_type_hints(type(self_instance))

                # Store dependency mapping for later resolution
                dependency_map = {}

                # For each dependency needed by the instance
                for dep_name, _dep_type in instance_hints.items():
                    # Check for direct match first (config -> config)
                    if dep_name in parent_hints:
                        dependency_map[dep_name] = dep_name
                    # Check for underscore prefix pattern (_config -> config)
                    elif dep_name.startswith("_"):
                        alt_name = dep_name[1:]  # Remove leading underscore
                        if alt_name in parent_hints:
                            dependency_map[dep_name] = alt_name

                # Store the dependency mapping for later use
                if dependency_map:
                    instance.__dict__["_dependency_map"] = dependency_map

                    # Set up the dependencies that are base references (not forwarded)
                    # These are dependencies that would be injected directly
                    # We need to defer this until after the instance is fully created
                    # to avoid circular dependencies
                    def setup_dependencies() -> None:
                        for dep_name, parent_attr in dependency_map.items():
                            # Resolve the dependency from the parent
                            try:
                                dep_value = getattr(self_instance, parent_attr)
                                setattr(instance, dep_name, dep_value)
                            except AttributeError:
                                # If the dependency can't be resolved, skip it
                                pass

                    # Store the setup function to be called later
                    instance.__dict__["_setup_dependencies"] = setup_dependencies

                    # Also set up __getattribute__ to call setup when dependencies are accessed
                    original_getattribute = instance.__class__.__getattribute__

                    def patched_getattribute(self: Any, name: str) -> Any:
                        # Call setup if it exists and we're accessing a dependency
                        if name in dependency_map:
                            try:
                                setup_func = self.__dict__.get("_setup_dependencies")
                                if setup_func:
                                    setup_func()
                                    del self.__dict__["_setup_dependencies"]
                            except (KeyError, AttributeError):
                                pass

                        return original_getattribute(self, name)

                    instance.__class__.__getattribute__ = patched_getattribute

            return instance

        except Exception as e:
            raise TypeError(
                f"Failed to create {attr_name}: {attr_type.__name__}: {e}"
            ) from e

    # Apply caching strategy
    if caching_strategy == CachingStrategy.NOT_THREAD_SAFE:
        return cached_property(factory)
    if caching_strategy == CachingStrategy.DISABLED:
        return property(factory)
    raise ValueError(f"Unsupported caching strategy: {caching_strategy}")


def _apply_module_decorator(
    cls: Type[Any], caching_strategy: CachingStrategy
) -> Type[Any]:
    """Apply the module decorator to a class.

    Args:
        cls: The class to decorate.
        caching_strategy: The caching strategy to use.

    Returns:
        The decorated class with factory methods.

    Raises:
        TypeError: If any dependency cannot be satisfied (greedy behavior).
    """
    # Get all type hints for the class
    hints = get_all_type_hints(cls)

    # Process each annotated attribute
    for attr_name, attr_type in hints.items():
        # Skip if this attribute doesn't need implementation
        if not needs_implementation(cls, attr_name):
            continue

        # Skip if property already exists
        if hasattr(cls, attr_name):
            continue

        # Validate that we can create this type (greedy behavior)
        if not _can_create_type(attr_type):
            # Check if it's a primitive type - if so, skip it silently
            # since it's likely being handled by another decorator
            primitive_types = (int, float, str, bool, bytes, complex, list, dict, tuple, set, frozenset)
            if attr_type in primitive_types:
                continue
            raise TypeError(f"Unsatisfied dependency: {attr_name}: {attr_type}")

        # Create factory method
        factory_method = _create_factory_method(attr_name, attr_type, caching_strategy)
        setattr(cls, attr_name, factory_method)

        # Call __set_name__ if it exists (required for cached_property)
        if hasattr(factory_method, "__set_name__"):
            factory_method.__set_name__(cls, attr_name)

    return cls


def _can_create_type(attr_type: Any) -> bool:
    """Check if a type can be created (greedy validation).

    Args:
        attr_type: The type to validate.

    Returns:
        True if the type can be created, False otherwise.
    """
    # Handle None and Any
    if attr_type is None or attr_type is Any:
        return False

    # Handle string type annotations (forward references)
    if isinstance(attr_type, str):
        return False  # Cannot create from string  # type: ignore

    # Handle primitive types - these should not be created as dependencies
    primitive_types = (int, float, str, bool, bytes, complex)
    if attr_type in primitive_types:
        return False

    # Handle built-in container types
    builtin_types = (list, dict, tuple, set, frozenset)
    if attr_type in builtin_types:
        return False

    # Check if it's a class that can be instantiated
    try:
        if not hasattr(attr_type, "__init__"):
            return False

        # Only create dependencies for custom classes, not built-in types
        return attr_type.__module__ != "builtins"
    except (TypeError, AttributeError):
        return False


def module(
    cls_or_strategy: Union[type, CachingStrategy, None] = None, /
) -> Union[type, Callable[[type], type]]:
    """Module decorator for dependency injection.

    This decorator automatically creates factory methods for annotated
    attributes, implementing dependency injection with configurable caching.
    It uses greedy behavior, raising errors for unsatisfied dependencies.

    Args:
        cls_or_strategy: Either a class to decorate directly, or a caching strategy.

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
    # Default caching strategy
    default_strategy = CachingStrategy.NOT_THREAD_SAFE

    # Handle different call patterns
    if cls_or_strategy is None:
        # @module() - empty parentheses
        return lambda cls: _apply_module_decorator(cls, default_strategy)
    if isinstance(cls_or_strategy, CachingStrategy):
        # @module(CachingStrategy.NOT_THREAD_SAFE) - with strategy
        return lambda cls: _apply_module_decorator(cls, cls_or_strategy)
    # @module - no parentheses, direct class decoration
    return _apply_module_decorator(cls_or_strategy, default_strategy)
