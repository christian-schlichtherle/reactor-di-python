"""Law of Demeter decorator for property forwarding.

This decorator implements the Law of Demeter principle by automatically
creating forwarding properties for annotated attributes. It uses reluctant
behavior, silently skipping attributes that cannot be resolved.
"""

import inspect
from typing import Any, Callable, Type

from .type_utils import (
    DEPENDENCY_MAP_ATTR,
    PARENT_INSTANCE_ATTR,
    SETUP_DEPENDENCIES_ATTR,
    get_alternative_names,
    has_constructor_assignment,
    safely_get_type_hints,
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
                    cls = type(parent)
                    parent_hints = safely_get_type_hints(cls)

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


def _can_resolve_attribute(
    cls: Type[Any],
    base_ref: str,
    target_attr_name: str,
) -> bool:
    """Check if an attribute can be resolved through static analysis.

    Multi-layer attribute detection strategy that checks:
    1. Static analysis (annotations, class attributes)
    2. Constructor evidence (without execution)
    3. Supports deferred resolution for dynamic attributes

    Handles problematic type annotations gracefully by catching exceptions
    during type inspection and constructor signature analysis. Returns False
    conservatively when static analysis cannot be performed.

    Args:
        cls: The class being decorated.
        base_ref: The base reference attribute name.
        target_attr_name: The target attribute name to resolve.

    Returns:
        True if attribute can be resolved, False otherwise.
        Returns False conservatively when type inspection fails.

    Example:
        >>> class Config:
        ...     timeout: int = 30
        >>> class Service:
        ...     config: Config
        >>> _can_resolve_attribute(Service, "config", "timeout")
        True
    """
    # First, check if the base reference exists in class annotations
    hints = safely_get_type_hints(cls)
    if base_ref in hints:
        base_type = hints[base_ref]

        if hasattr(base_type, target_attr_name):
            return True
        if isinstance(base_type, str):
            return True  # Use deferred resolution for forward references
        if not inspect.isclass(base_type):
            return True  # Use deferred resolution for complex types

        target_hints = safely_get_type_hints(base_type)
        if target_attr_name in target_hints:
            return True

        return has_constructor_assignment(base_type, target_attr_name)

    # If base_ref is not in annotations, check if it might be set at runtime
    # For runtime attributes like _module (set in __init__), we need to be more
    # careful about which attributes we try to resolve

    # Try to infer the type by looking at constructor parameters
    if hasattr(cls, "__init__"):
        try:
            sig = inspect.signature(cls.__init__)
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue

                # Check if this parameter might correspond to our base_ref
                alt_names = get_alternative_names(base_ref)
                if param_name == base_ref or param_name in alt_names:
                    if param.annotation != inspect.Parameter.empty:
                        # We found a type annotation for the parameter
                        param_type = param.annotation

                        # Now check if the target attribute exists on this type
                        try:
                            if inspect.isclass(param_type):
                                target_hints = safely_get_type_hints(param_type)
                                if target_attr_name in target_hints:
                                    return True
                                if hasattr(param_type, target_attr_name):
                                    return True

                                # Check constructor assignments
                                if has_constructor_assignment(
                                    param_type, target_attr_name
                                ):
                                    return True
                        except (TypeError, OSError):
                            pass
                    else:
                        # No type annotation, but parameter exists
                        # This is more speculative, but if the user explicitly specified
                        # this base_ref, we should trust them and use deferred resolution
                        return True
        except (TypeError, ValueError):
            pass

    # If we can't determine the type, be conservative
    return False


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
        # Process each annotated attribute
        for attr_name, attr_type in safely_get_type_hints(cls).items():
            # Special case: if this is the base reference itself, it must not get forwarded
            if attr_name == base_ref:
                continue
            if hasattr(cls, attr_name):
                continue
            if not attr_name.startswith(prefix):
                continue

            target_attr_name = attr_name[len(prefix) :]
            if not _can_resolve_attribute(cls, base_ref, target_attr_name):
                continue

            # Always use deferred resolution to avoid recursion issues
            deferred_prop = DeferredProperty(base_ref, target_attr_name, attr_type)
            setattr(cls, attr_name, deferred_prop)

        return cls

    return decorator
