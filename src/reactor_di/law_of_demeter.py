"""Law of Demeter decorator for property forwarding.

This decorator implements the Law of Demeter principle by automatically
creating forwarding properties for annotated attributes. It uses reluctant
behavior, silently skipping attributes that cannot be resolved.
"""

from typing import Any, Callable, Type

from .type_utils import (
    can_resolve_attribute,
    get_all_type_hints,
    needs_implementation,
)


class DeferredProperty:
    """Property that resolves target existence at first access.

    This class implements deferred resolution for attributes that cannot
    be statically proven to exist, such as constructor-created attributes.
    """

    def __init__(self, base_ref: str, target_attr_name: str, expected_type: Any):
        """Initialize deferred property.

        Args:
            base_ref: Name of the base reference attribute.
            target_attr_name: Name of the target attribute to forward.
            expected_type: Expected type of the target attribute.
        """
        self.base_ref = base_ref
        self.target_attr_name = target_attr_name
        self.expected_type = expected_type
        self._resolved_property = None

    def __get__(self, instance: Any, owner: Type[Any]) -> Any:
        """Get the forwarded attribute value.

        Args:
            instance: The instance accessing the property.
            owner: The class that owns the property.

        Returns:
            The forwarded attribute value.

        Raises:
            AttributeError: If runtime resolution fails.
        """
        if instance is None:
            return self

        # Always try to resolve dynamically, don't cache the resolution
        # This is necessary for attributes that might be created during construction

        # First check if there's a setup function that needs to be called
        if hasattr(instance, "_setup_dependencies"):
            setup_func = instance._setup_dependencies
            setup_func()
            # Remove the setup function after calling it
            delattr(instance, "_setup_dependencies")

        try:
            base_obj = getattr(instance, self.base_ref)
        except AttributeError:
            # Try to resolve from parent instance if available
            if hasattr(instance, "_parent_instance"):
                parent = instance._parent_instance

                # Check if there's a dependency mapping for this attribute
                if (
                    hasattr(instance, "_dependency_map")
                    and self.base_ref in instance._dependency_map
                ):
                    parent_attr = instance._dependency_map[self.base_ref]
                    base_obj = getattr(parent, parent_attr)

                    # Set the dependency as an instance attribute for future access
                    setattr(instance, self.base_ref, base_obj)
                else:
                    # Fallback to type hints checking
                    parent_hints = get_all_type_hints(type(parent))

                    # Try exact match first
                    if self.base_ref in parent_hints:
                        base_obj = getattr(parent, self.base_ref)
                    # Try without underscore prefix
                    elif self.base_ref.startswith("_"):
                        alt_name = self.base_ref[1:]
                        if alt_name in parent_hints:
                            base_obj = getattr(parent, alt_name)
                        else:
                            raise AttributeError(
                                f"Runtime resolution failed: {self.base_ref} not found on {owner.__name__} or parent"
                            ) from None
                    else:
                        raise AttributeError(
                            f"Runtime resolution failed: {self.base_ref} not found on {owner.__name__} or parent"
                        ) from None
            else:
                raise AttributeError(
                    f"Runtime resolution failed: {self.base_ref} not found on {owner.__name__}"
                ) from None

        # Handle None base_obj (might be set during construction)
        if base_obj is None:
            raise AttributeError(f"Runtime resolution failed: {self.base_ref} is None")

        # Try to get the attribute, with fallback to underscore prefix
        try:
            return getattr(base_obj, self.target_attr_name)
        except AttributeError:
            # Try with underscore prefix if the direct attribute doesn't exist
            if not self.target_attr_name.startswith("_"):
                alt_target_attr_name = "_" + self.target_attr_name
                try:
                    return getattr(base_obj, alt_target_attr_name)
                except AttributeError:
                    pass

            raise AttributeError(
                f"Runtime resolution failed: {self.base_ref}.{self.target_attr_name} not found"
            ) from None

    def _create_forwarding_property(self) -> property:
        """Create a forwarding property for the resolved attribute."""

        def getter(self_instance: Any) -> Any:
            base_obj = getattr(self_instance, self.base_ref)
            return getattr(base_obj, self.target_attr_name)

        def setter(self_instance: Any, value: Any) -> None:
            base_obj = getattr(self_instance, self.base_ref)
            setattr(base_obj, self.target_attr_name, value)

        return property(getter, setter)


def _create_static_property(base_ref: str, target_attr_name: str) -> property:
    """Create a static forwarding property.

    Args:
        base_ref: Name of the base reference attribute.
        target_attr_name: Name of the target attribute to forward.

    Returns:
        A property that forwards attribute access.
    """

    def getter(self_instance: Any) -> Any:
        base_obj = getattr(self_instance, base_ref)
        return getattr(base_obj, target_attr_name)

    def setter(self_instance: Any, value: Any) -> None:
        base_obj = getattr(self_instance, base_ref)
        setattr(base_obj, target_attr_name, value)

    return property(getter, setter)


def _is_primitive_type(attr_type: Any) -> bool:
    """Check if a type is a primitive type that should not be forwarded.

    Args:
        attr_type: The type to check.

    Returns:
        True if it's a primitive type, False otherwise.
    """
    # Handle None and Any
    if attr_type is None or attr_type is Any:
        return True

    # Handle primitive types
    primitive_types = (int, float, str, bool, bytes, complex)
    if attr_type in primitive_types:
        return True

    # Handle built-in container types
    builtin_types = (list, dict, tuple, set, frozenset)
    return attr_type in builtin_types


def law_of_demeter(
    base_ref: str,
    *,
    prefix: str = "_",
) -> Callable[[Type[Any]], Type[Any]]:
    """Law of Demeter decorator for property forwarding.

    This decorator automatically creates forwarding properties for annotated
    attributes, following the Law of Demeter principle. It implements reluctant
    behavior by silently skipping attributes that cannot be resolved.

    Args:
        base_ref: Name of the base reference attribute to forward from.
        prefix: Prefix for generated property names (default: "_").

    Returns:
        A decorator function that modifies the class.

    Example:
        >>> class Config:
        ...     timeout: int = 30
        >>> @law_of_demeter("config")
        ... class Service:
        ...     config: Config
        ...     timeout: int  # Will be forwarded from config.timeout
        >>> service = Service()
        >>> service.config = Config()
        >>> service.timeout
        30
    """

    def decorator(cls: Type[Any]) -> Type[Any]:
        """Apply the Law of Demeter decorator to a class.

        Args:
            cls: The class to decorate.

        Returns:
            The decorated class with forwarding properties.
        """
        # Get all type hints for the class
        hints = get_all_type_hints(cls)

        # Use the base_ref as provided - no hardcoded aliases
        actual_base_ref = base_ref

        # Process each annotated attribute
        for attr_name, attr_type in hints.items():
            # Skip if this attribute doesn't need implementation
            if not needs_implementation(cls, attr_name):
                continue

            # The property name is the annotated attribute name
            property_name = attr_name

            # Skip if property already exists
            if hasattr(cls, property_name):
                continue

            # The base reference should be available as a dependency, not skipped
            # This allows it to be injected by the @module decorator
            # if attr_name == actual_base_ref:
            #     continue

            # Extract target attribute name by removing prefix if present
            if prefix and attr_name.startswith(prefix):
                target_attr_name = attr_name[len(prefix) :]
            elif prefix == "":
                # If prefix is empty, process all attributes
                target_attr_name = attr_name
            else:
                # If prefix is specified but attribute doesn't start with it, skip
                continue

            # Special case: if this is the base reference itself,
            # it should be injected directly, not forwarded
            if attr_name == actual_base_ref:
                continue

            # Check if we can resolve this attribute (reluctant behavior)
            if can_resolve_attribute(cls, actual_base_ref, target_attr_name):
                # Always use deferred resolution to avoid recursion issues
                deferred_prop = DeferredProperty(
                    actual_base_ref, target_attr_name, attr_type
                )
                setattr(cls, property_name, deferred_prop)
            # If we can't resolve it, silently skip (reluctant behavior)

        return cls

    return decorator
