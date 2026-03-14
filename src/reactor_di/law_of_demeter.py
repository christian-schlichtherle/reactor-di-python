"""Law of Demeter decorator for property forwarding.

This decorator implements the Law of Demeter principle by automatically
creating forwarding properties for annotated attributes. It uses reluctant
behavior, silently skipping attributes that cannot be resolved.
"""

import inspect
from typing import Any, Callable, get_type_hints

from .type_utils import (
    SETUP_DEPENDENCIES_ATTR,
    get_alternative_names,
    has_constructor_assignment,
    is_lookup_type,
    resolve_abstract_property_conflicts,
    unwrap_lookup,
)


class _DeferredProperty:
    """Property that resolves target existence at first access.

    This class implements deferred resolution for attributes that cannot
    be statically proven to exist, such as constructor-created attributes.
    """

    def __init__(
        self,
        base_ref: str,
        target_attr_name: str,
    ):
        """Initialize deferred property.

        Args:
            base_ref: Name of the base reference attribute.
            target_attr_name: Name of the target attribute to forward.
            expected_type: Expected type of the target attribute.
        """
        self.base_ref = base_ref
        self.target_attr_name = target_attr_name

    def __get__(self, instance: Any, owner: type[Any]) -> Any:
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

        # Check instance dict directly to avoid triggering __getattr__,
        # which would attempt dependency resolution for an internal attr name.
        setup_func = instance.__dict__.pop(SETUP_DEPENDENCIES_ATTR, None)
        if setup_func is not None:
            setup_func()

        # Resolve the base reference and forward the attribute.
        # If the base ref isn't in the instance dict, this may trigger
        # __getattr__ for lazy dependency resolution from the module.
        base_obj = getattr(instance, self.base_ref)

        return getattr(base_obj, self.target_attr_name)


def _can_resolve_attribute(
    class_type: type[Any],
    base_ref: str,
    target_attr_name: str,
) -> bool:
    """Check if an attribute can be resolved through static analysis.

    Performs a two-stage attribute detection:
    1. Type hints checking - verifies if base_ref has the target attribute
    2. Constructor parameter inference - checks __init__ parameters for type info

    This simplified approach removed complex error handling as Python 3.8+
    provides stable type hint APIs that don't require defensive coding.

    Args:
        class_type: The class being decorated.
        base_ref: The base reference attribute name.
        target_attr_name: The target attribute name to resolve.

    Returns:
        True if attribute can be resolved, False otherwise.
        Returns False conservatively when the attribute cannot be proven to exist.

    Example:
        >>> class Config:
        ...     timeout: int = 30
        >>> class Service:
        ...     config: Config
        >>> _can_resolve_attribute(Service, "config", "timeout")
        True
    """
    # First, check if the base reference exists in class annotations
    if base_type := unwrap_lookup(get_type_hints(class_type).get(base_ref)):
        if hasattr(base_type, target_attr_name):
            return True

        # Check type hints (catches Pydantic/dataclass fields that are
        # annotations without class-level attributes)
        if target_attr_name in get_type_hints(base_type):
            return True

        return has_constructor_assignment(base_type, target_attr_name)

    # Fall back to constructor parameter analysis
    # This handles cases where base_ref is passed as a parameter

    # Try to infer the type by looking at constructor parameters
    params = list(inspect.signature(class_type.__init__).parameters.items())
    for param_name, param in params[1:]:  # skip first parameter (self or cls)
        # Check if this parameter might correspond to our base_ref
        if param_name in get_alternative_names(base_ref):
            if param.annotation != inspect.Parameter.empty:
                # We found a type annotation for the parameter
                param_type = param.annotation

                # Now check if the target attribute exists on this type
                if inspect.isclass(param_type):
                    if target_attr_name in get_type_hints(param_type):
                        return True
                    if hasattr(param_type, target_attr_name):
                        return True

                    # Check constructor assignments
                    if has_constructor_assignment(param_type, target_attr_name):
                        return True
            else:
                # Parameter exists without type annotation
                # Trust the user's intent and allow deferred resolution
                return True

    # If we can't determine the type, be conservative
    return False


def law_of_demeter(
    base_ref: str,
    *,
    prefix: str = "_",
) -> Callable[[type[Any]], type[Any]]:
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

    def decorator(class_type: type[Any]) -> type[Any]:
        """Apply the Law of Demeter decorator to a class.

        Args:
            class_type: The class to decorate.

        Returns:
            The decorated class with forwarding properties.
        """
        # Resolve abstract @property conflicts before processing annotations.
        # If a parent ABC declares an abstract @property with the same name
        # as a DI annotation, install a concrete property backed by __dict__
        # so the class can be instantiated and DI resolution isn't shadowed.
        resolve_abstract_property_conflicts(class_type)

        # Process each annotated attribute
        for attr_name, attr_type in get_type_hints(class_type).items():
            # Special case: if this is the base reference itself, it must not get forwarded
            if attr_name == base_ref:
                continue
            if hasattr(class_type, attr_name):
                continue
            # lookup[] dependencies come from the parent module, not the base ref
            if is_lookup_type(attr_type):
                continue
            if not attr_name.startswith(prefix):
                continue

            target_attr_name = attr_name[len(prefix) :]
            if not _can_resolve_attribute(class_type, base_ref, target_attr_name):
                continue

            # Always use deferred resolution to avoid recursion issues
            deferred_prop = _DeferredProperty(base_ref, target_attr_name)
            setattr(class_type, attr_name, deferred_prop)

        return class_type

    return decorator
