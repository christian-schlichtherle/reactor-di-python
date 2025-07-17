"""Type utilities for dependency injection and attribute resolution.

This module provides comprehensive type checking and analysis utilities
for the reactor-di dependency injection system. It handles complex type
hierarchies, inheritance patterns, and attribute resolution.
"""

import inspect
from typing import Any, Dict, Type, get_type_hints


def get_all_type_hints(cls: Type[Any]) -> Dict[str, Any]:
    """Get all type hints from a class, including inherited annotations.

    Traverses the Method Resolution Order (MRO) to collect all type hints
    from the class and its parent classes, with child class annotations
    taking precedence over parent class annotations.

    Args:
        cls: The class to analyze for type hints.

    Returns:
        Dictionary mapping attribute names to their type annotations.

    Example:
        >>> class Parent:
        ...     x: int
        >>> class Child(Parent):
        ...     y: str
        >>> hints = get_all_type_hints(Child)
        >>> 'x' in hints and 'y' in hints
        True
    """
    all_hints: Dict[str, Any] = {}

    # Traverse MRO in reverse order so child classes override parent classes
    for base in reversed(cls.__mro__):
        if base is object:
            continue

        try:
            # Get type hints for this class in the MRO
            base_hints = get_type_hints(base)
            all_hints.update(base_hints)
        except (TypeError, NameError, AttributeError):
            # Handle cases where type hints can't be resolved
            # This can happen with forward references or complex generics
            continue

    return all_hints


def safe_get_type_hints(cls: Type[Any]) -> Dict[str, Any]:
    """Safely get type hints with fallback handling for edge cases.

    This function provides a safe wrapper around get_type_hints that
    handles various edge cases like forward references, missing imports,
    and complex generic types.

    Args:
        cls: The class to analyze for type hints.

    Returns:
        Dictionary mapping attribute names to their type annotations.
        Returns empty dict if type hints cannot be resolved.

    Example:
        >>> class Example:
        ...     x: int
        ...     y: "ForwardRef"  # Forward reference
        >>> hints = safe_get_type_hints(Example)
        >>> 'x' in hints
        True
    """
    try:
        return get_type_hints(cls)
    except (TypeError, NameError, AttributeError):
        # Fallback to raw annotations if type hints can't be resolved
        try:
            return getattr(cls, "__annotations__", {})
        except AttributeError:
            return {}


def needs_implementation(cls: Type[Any], attr_name: str) -> bool:
    """Check if an attribute needs implementation (synthesis).

    Determines whether an attribute needs to be synthesized by checking
    if it already exists in the class hierarchy. This traverses the entire
    MRO to ensure comprehensive checking.

    Args:
        cls: The class to check for the attribute.
        attr_name: Name of the attribute to check.

    Returns:
        True if the attribute needs implementation, False if it already exists.

    Example:
        >>> class Example:
        ...     existing_attr = "value"
        >>> needs_implementation(Example, "existing_attr")
        False
        >>> needs_implementation(Example, "missing_attr")
        True
    """
    # Check if attribute exists in class hierarchy
    for base in cls.__mro__:
        if hasattr(base, attr_name):
            attr = getattr(base, attr_name)
            # Skip if it's just a type annotation without value
            if not (inspect.isclass(attr) and attr.__name__ == attr_name):
                return False

    return True


def is_type_compatible(expected_type: Any, actual_type: Any) -> bool:
    """Check if two types are compatible for dependency injection.

    Performs conservative type compatibility checking that handles
    common cases while gracefully handling complex type hierarchies.

    Args:
        expected_type: The expected type annotation.
        actual_type: The actual type to check compatibility against.

    Returns:
        True if types are compatible, False otherwise.
        Conservative approach returns True for complex cases.

    Example:
        >>> is_type_compatible(int, int)
        True
        >>> is_type_compatible(str, int)
        False
        >>> class Parent: pass
        >>> class Child(Parent): pass
        >>> is_type_compatible(Parent, Child)
        True
    """
    # Handle None/Any cases
    if expected_type is None or actual_type is None:
        return True

    # Handle Any type
    if expected_type is Any or actual_type is Any:
        return True

    # Handle string type annotations (forward references)
    if isinstance(expected_type, str) or isinstance(actual_type, str):
        return True  # Conservative approach for forward references

    # Handle exact type matches
    if expected_type == actual_type:
        return True

    # Handle class inheritance
    try:
        if inspect.isclass(expected_type) and inspect.isclass(actual_type):
            return issubclass(actual_type, expected_type)
    except TypeError:
        # Handle complex generic types gracefully
        pass

    # Handle generic types and complex annotations
    try:
        # For complex type annotations, use string representation as fallback
        if hasattr(expected_type, "__origin__") or hasattr(actual_type, "__origin__"):
            return True  # Conservative approach for generics
    except (TypeError, AttributeError):
        pass

    # Conservative fallback - assume compatibility for complex cases
    return True


def can_resolve_attribute(cls: Type[Any], base_ref: str, target_attr_name: str) -> bool:
    """Check if an attribute can be resolved through static analysis.

    Multi-layer attribute detection strategy that checks:
    1. Static analysis (annotations, class attributes)
    2. Constructor evidence (without execution)
    3. Supports deferred resolution for dynamic attributes

    Args:
        cls: The class being decorated.
        base_ref: The base reference attribute name.
        target_attr_name: The target attribute name to resolve.

    Returns:
        True if attribute can be resolved, False otherwise.

    Example:
        >>> class Config:
        ...     timeout: int = 30
        >>> class Service:
        ...     config: Config
        >>> can_resolve_attribute(Service, "config", "timeout")
        True
    """
    # First, check if the base reference exists in class annotations
    hints = get_all_type_hints(cls)
    if base_ref in hints:
        base_type = hints[base_ref]

        # Handle string type annotations (forward references)
        if isinstance(base_type, str):
            return True  # Use deferred resolution for forward references

        # Check if base_type is a class we can analyze
        if not inspect.isclass(base_type):
            return True  # Use deferred resolution for complex types

        # Check if target attribute exists in the base type
        try:
            target_hints = get_all_type_hints(base_type)
            if target_attr_name in target_hints:
                return True

            # Check class attributes
            if hasattr(base_type, target_attr_name):
                return True

            # Check if this might be a constructor-created attribute
            # by looking for simple patterns in the constructor
            if hasattr(base_type, "__init__"):
                try:
                    source = inspect.getsource(base_type.__init__)
                    # Look for assignment pattern: self.target_attr_name =
                    if f"self.{target_attr_name} =" in source:
                        return True
                except (OSError, TypeError):
                    pass

        except (TypeError, AttributeError):
            # Handle edge cases gracefully
            pass

        # For attributes that can't be statically proven, return False
        # This ensures we only create properties for attributes we can reasonably expect to exist
        return False

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
                # Pattern 1: Direct match (config parameter for config base_ref)
                # Pattern 2: Underscore prefix (_module base_ref from module parameter)
                if (param_name == base_ref or
                    (base_ref.startswith("_") and param_name == base_ref[1:])):
                    if param.annotation != inspect.Parameter.empty:
                        # We found a type annotation for the parameter
                        param_type = param.annotation

                        # Now check if the target attribute exists on this type
                        try:
                            if inspect.isclass(param_type):
                                target_hints = get_all_type_hints(param_type)
                                if target_attr_name in target_hints:
                                    return True
                                if hasattr(param_type, target_attr_name):
                                    return True

                                # Check constructor assignments
                                if hasattr(param_type, "__init__"):
                                    source = inspect.getsource(param_type.__init__)
                                    # Look for assignment pattern: self.target_attr_name =
                                    if f"self.{target_attr_name} =" in source:
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


def get_attribute_type(cls: Type[Any], attr_name: str) -> Any:
    """Get the type annotation for an attribute.

    Retrieves the type annotation for a given attribute name from
    the class hierarchy.

    Args:
        cls: The class to check for the attribute type.
        attr_name: Name of the attribute to get the type for.

    Returns:
        The type annotation for the attribute, or None if not found.

    Example:
        >>> class Example:
        ...     x: int
        >>> get_attribute_type(Example, "x") is int
        True
    """
    hints = get_all_type_hints(cls)
    return hints.get(attr_name, None)
