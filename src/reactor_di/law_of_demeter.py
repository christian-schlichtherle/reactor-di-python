"""Law of Demeter decorator for property forwarding.

This decorator implements the Law of Demeter principle by automatically
creating forwarding properties for annotated attributes. It uses reluctant
behavior, silently skipping attributes that cannot be resolved.
"""

from typing import Any, Callable, Type

from .type_utils import (
    DEPENDENCY_MAP_ATTR,
    PARENT_INSTANCE_ATTR,
    SETUP_DEPENDENCIES_ATTR,
    can_resolve_attribute,
    get_all_type_hints,
    get_alternative_names,
    needs_implementation,
)


class DeferredProperty:
    """Property that resolves target existence at first access.

    This class implements deferred resolution for attributes that cannot
    be statically proven to exist, such as constructor-created attributes.
    """

    def __init__(
        self,
        base_ref: str,
        target_attr_name: str,
        expected_type: Any,
    ):
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
        setup_attr = SETUP_DEPENDENCIES_ATTR
        if hasattr(instance, setup_attr):
            setup_func = getattr(instance, setup_attr)
            setup_func()
            # Remove the setup function after calling it
            delattr(instance, setup_attr)

        try:
            base_obj = getattr(instance, self.base_ref)
        except AttributeError:
            # Try to resolve from parent instance if available
            parent_attr = PARENT_INSTANCE_ATTR
            if hasattr(instance, parent_attr):
                parent = getattr(instance, parent_attr)

                # Check if there's a dependency mapping for this attribute
                dependency_map_attr = DEPENDENCY_MAP_ATTR
                if hasattr(instance, dependency_map_attr) and self.base_ref in getattr(
                    instance, dependency_map_attr
                ):
                    dependency_map = getattr(instance, dependency_map_attr)
                    parent_attr_name = dependency_map[self.base_ref]
                    base_obj = getattr(parent, parent_attr_name)

                    # Set the dependency as an instance attribute for future access
                    setattr(instance, self.base_ref, base_obj)
                else:
                    # Fallback to type hints checking
                    parent_hints = get_all_type_hints(type(parent))

                    # Try exact match first
                    if self.base_ref in parent_hints:
                        base_obj = getattr(parent, self.base_ref)
                    # Try alternative names based on naming configuration
                    else:
                        alt_names = get_alternative_names(self.base_ref)
                        base_obj = None
                        for alt_name in alt_names:
                            if alt_name in parent_hints:
                                base_obj = getattr(parent, alt_name)
                                break

                        if base_obj is None:
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

        # Try to get the attribute, with fallback to alternative names
        try:
            return getattr(base_obj, self.target_attr_name)
        except AttributeError:
            # Try alternative names based on naming configuration
            alt_names = get_alternative_names(self.target_attr_name)
            for alt_name in alt_names:
                if alt_name != self.target_attr_name:  # Don't retry the same name
                    return getattr(base_obj, alt_name)

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
        prefix: Prefix for generated property names (default: \"_\").

    Returns:
        A decorator function that modifies the class.

    Example:
        >>> class Config:
        ...     timeout: int = 30
        >>> @law_of_demeter("config")
        ... class Service:
        ...     config: Config
        ...     _timeout: int  # Will be forwarded from config.timeout
        >>> service = Service()
        >>> service.config = Config()
        >>> service._timeout
        30
    """

    def decorator(cls: Type[Any]) -> Type[Any]:
        """Apply the Law of Demeter decorator to a class.

        Args:
            cls: The class to decorate.

        Returns:
            The decorated class with forwarding properties.
        """
        # Use the provided prefix directly
        effective_prefix = prefix

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

            # Extract target attribute name by removing prefix
            if effective_prefix and attr_name.startswith(effective_prefix):
                target_attr_name = attr_name[len(effective_prefix) :]
            elif effective_prefix == "":
                target_attr_name = attr_name
            else:
                # If prefix is specified but attribute doesn't match, skip
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
