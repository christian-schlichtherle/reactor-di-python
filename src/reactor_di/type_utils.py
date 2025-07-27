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
    that have forward-references to undefined classes, invalid type syntax,
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

    def safely_get_type_hints(base: Type[Any]) -> Dict[str, Any]:
        """Safely get type hints from a base class."""
        try:
            return get_type_hints(base)
        except (TypeError, NameError, AttributeError, SyntaxError):
            return {}

    # Dictionary comprehension with nested iteration
    return {
        key: value
        for base in reversed(cls.__mro__)
        if base is not object
        for key, value in safely_get_type_hints(base).items()
    }


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
        alternatives.append(name[len(default_prefix):])

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

    Uses regex pattern matching to detect both standard assignments (instance.attr = value)
    and type-annotated assignments (instance.attr: Type = value) in constructor source code.
    Dynamically determines the first parameter name instead of hardcoding "self".
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
        # Get the first parameter name from the constructor signature, which is usually "self", but could be anything
        self = next(iter(inspect.signature(class_type.__init__).parameters))

        source = inspect.getsource(class_type.__init__)
        # Use combined regex pattern to match both assignment and type annotation
        # Matches: self.attr = value OR self.attr: Type = value
        return bool(re.search(rf"{re.escape(self)}\s*\.\s*{re.escape(attr_name)}\s*[=:]", source))
    except (OSError, TypeError, ValueError):
        return False
