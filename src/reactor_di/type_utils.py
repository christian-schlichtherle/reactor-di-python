"""Type utilities for dependency injection and attribute resolution.

This module provides comprehensive type checking and analysis utilities
for the Reactor DI dependency injection system. It handles complex type
hierarchies, inheritance patterns, and attribute resolution with robust
error handling for edge cases in Python's type system.

Key features:
- Defensive error handling for built-in classes and compiled extensions
- Graceful handling of forward references and invalid type syntax
- Conservative fallback behavior for problematic type annotations
- Efficient regex-based constructor analysis with combined patterns
"""

import inspect
import re
from typing import Any, Dict, Final, List, Tuple, Type, get_type_hints

# Constants for internal attribute names
DEPENDENCY_MAP_ATTR: Final[str] = "_reactor_di_dependency_map"
PARENT_INSTANCE_ATTR: Final[str] = "_reactor_di_parent_instance"
SETUP_DEPENDENCIES_ATTR: Final[str] = "_reactor_di_setup_dependencies"

PRIMITIVE_EQUIVALENT_TYPES: Final[Tuple[Type[Any], ...]] = (
    int,
    float,
    str,
    bool,
    bytes,
    complex,
    list,
    dict,
    tuple,
    set,
    frozenset,
)


def get_all_type_hints(cls: Type[Any]) -> Dict[str, Any]:
    """Get all type hints from a class, including inherited annotations.

    Traverses the Method Resolution Order (MRO) to collect all type hints
    from the class and its parent classes, with child class annotations
    taking precedence over parent class annotations.

    Handles problematic type annotations gracefully by skipping classes
    that have forward references to undefined classes, invalid type syntax,
    or other issues that prevent type hint resolution.

    Args:
        cls: The class to analyze for type hints.

    Returns:
        Dictionary mapping attribute names to their type annotations.
        Returns empty dict if no type hints can be resolved.

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
        except (TypeError, NameError, AttributeError, SyntaxError):
            # Handle cases where type hints can't be resolved
            # This can happen with forward references or complex generics
            continue

    return all_hints


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
            # Skip unless it's a type annotation without value
            if not (inspect.isclass(attr) and attr.__name__ == attr_name):
                return False

    return True


def get_alternative_names(name: str, default_prefix: str = "_") -> List[str]:
    """Generate alternative names based on naming conventions.

    Args:
        name: The base name to generate alternatives for.
        default_prefix: Default prefix to try removing/adding.

    Returns:
        List of alternative names to try.
    """
    alternatives = []

    # Remove default prefix if present
    if default_prefix and name.startswith(default_prefix):
        alternatives.append(name[len(default_prefix) :])

    # Add unprefixed version if not already included
    if name not in alternatives:
        alternatives.append(name)

    return alternatives


def is_primitive_type(attr_type: Any) -> bool:
    """Check if a type should be treated as primitive.

    Args:
        attr_type: The type to check.

    Returns:
        True if the type is primitive and should not be auto-instantiated.
    """
    if attr_type is None or attr_type is Any:
        return True

    return attr_type in PRIMITIVE_EQUIVALENT_TYPES


def should_create_dependency(attr_type: Any) -> bool:
    """Determine if a dependency should be automatically created.

    Args:
        attr_type: The type to check.

    Returns:
        True if the dependency should be created, False otherwise.
    """
    if not hasattr(attr_type, "__module__"):
        return True

    # Exclude builtins module
    if attr_type.__module__ == "builtins":
        return False

    # Check constructor requirement
    return hasattr(attr_type, "__init__")


def has_constructor_assignment(class_type: Type[Any], attr_name: str) -> bool:
    """Check if a class constructor assigns to a specific attribute.

    Uses regex pattern matching to detect both standard assignments (self.attr = value)
    and type-annotated assignments (self.attr: Type = value) in constructor source code.
    Handles edge cases gracefully by returning False for built-in classes, classes
    without __init__, and other scenarios where source code cannot be inspected.

    Args:
        class_type: The class to check.
        attr_name: The attribute name to look for in constructor.

    Returns:
        True if constructor assigns to the attribute, False otherwise.
        Returns False for built-in classes, compiled extensions, and other
        cases where source code inspection fails.
    """
    if not hasattr(class_type, "__init__"):
        return False

    try:
        source = inspect.getsource(class_type.__init__)
        # Use combined regex pattern to match both assignment and type annotation
        # Matches: self.attr = value OR self.attr: Type = value
        return bool(re.search(rf"self\s*\.\s*{re.escape(attr_name)}\s*[=:]", source))
    except (OSError, TypeError):
        return False


def can_resolve_attribute(
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
        target_hints = get_all_type_hints(base_type)
        if target_attr_name in target_hints:
            return True

        # Check class attributes
        if hasattr(base_type, target_attr_name):
            return True

        # Check if this might be a constructor-created attribute
        if has_constructor_assignment(base_type, target_attr_name):
            return True

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
                alt_names = get_alternative_names(base_ref)
                if param_name == base_ref or param_name in alt_names:
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
