"""
Shared type utilities for decorators.

This module contains common type checking and resolution utilities used by both
the @law_of_demeter and @module decorators. It can be copied independently to
other projects along with either decorator.

Key Functions:
- get_all_type_hints(): Collects type hints from entire inheritance hierarchy
- safe_get_type_hints(): Safely retrieves type hints with fallback to annotations
- needs_implementation(): Checks if an attribute needs implementation (searches full MRO for abstract attributes)
- is_type_compatible(): Validates type compatibility for dependency injection

The functions systematically search the Method Resolution Order (MRO) to find
annotations and abstract attributes from the entire class hierarchy, ensuring
proper decorator behavior with complex inheritance patterns.

Design Note:
The type compatibility logic prioritizes simplicity and realistic scenarios over
defensive programming. Exception handling for unrealistic edge cases has been
removed in favor of letting real errors propagate for proper debugging.
"""

import inspect
from typing import Any, Type, get_type_hints


def is_type_compatible(provided_type: Any, required_type: Any) -> bool:
    """Check if provided ingredient type is compatible with required ingredient type.

    Args:
        provided_type: The ingredient type that the module provides
        required_type: The ingredient type that the component requires

    Returns:
        True if provided_type can react with required_type
    """
    # Exact type match
    if provided_type == required_type:
        return True

    # Handle string type annotations
    if isinstance(provided_type, str) or isinstance(required_type, str):
        # For string annotations, we can only do name-based comparison
        provided_name = getattr(provided_type, "__name__", str(provided_type))
        required_name = getattr(required_type, "__name__", str(required_type))
        return provided_name == required_name

    # Handle None types
    if provided_type is None or required_type is None:
        return provided_type is required_type

    # Try subclass relationship for classes
    if inspect.isclass(provided_type) and inspect.isclass(required_type):
        return issubclass(provided_type, required_type)

    # For other complex types (generics, unions, etc.), be conservative
    # and allow them through - full type checking would require more
    # sophisticated tools like mypy's type system
    return True


def safe_get_type_hints(cls: Type[Any]) -> dict[str, Any]:
    """Safely get type hints, falling back to __annotations__ if needed.

    Args:
        cls: The class to get type hints for

    Returns:
        Dictionary of type hints
    """
    try:
        return get_type_hints(cls)
    except (NameError, AttributeError, TypeError):
        return getattr(cls, "__annotations__", {})


def get_all_type_hints(cls: Type[Any]) -> dict[str, Any]:
    """Get type hints from a class and all its superclasses.

    Walks the MRO (Method Resolution Order) to collect all type hints,
    with subclass annotations taking precedence over superclass ones.

    Args:
        cls: The class to get type hints for

    Returns:
        Dictionary of all type hints from the class hierarchy
    """
    all_hints = {}

    # Walk the MRO in reverse order so subclass annotations override superclass ones
    for base_cls in reversed(cls.__mro__):
        if base_cls is object:
            continue

        # Get hints for this class
        base_hints = safe_get_type_hints(base_cls)
        all_hints.update(base_hints)

    return all_hints


def needs_implementation(cls: Type[Any], attr_name: str) -> bool:
    """Check if annotation/attribute needs implementation.

    Returns True if:
    - Attribute has annotation but no implementation
    - Attribute is an abstract method/property (searches entire inheritance hierarchy)

    Args:
        cls: The class to check
        attr_name: The attribute name to check

    Returns:
        True if the attribute needs implementation
    """
    # Get annotations from entire inheritance hierarchy
    annotations = get_all_type_hints(cls)

    # Has annotation but no implementation
    if attr_name in annotations and not hasattr(cls, attr_name):
        return True

    # Search inheritance hierarchy for abstract attributes/properties
    for base_cls in cls.__mro__:
        if base_cls is object:
            continue

        # Check if this class defines the attribute
        if attr_name in base_cls.__dict__:
            attr = base_cls.__dict__[attr_name]

            # Direct abstract method
            if hasattr(attr, "__isabstractmethod__") and attr.__isabstractmethod__:
                return True

            # cached_property with abstract underlying function
            if (
                hasattr(attr, "func")
                and hasattr(attr.func, "__isabstractmethod__")
                and attr.func.__isabstractmethod__
            ):
                return True

    return False
