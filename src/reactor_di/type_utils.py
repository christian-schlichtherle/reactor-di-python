"""Type utilities for dependency injection and attribute resolution.

Provides type checking and analysis utilities for the Reactor DI system.
Simplified after removing unnecessary defensive programming - Python 3.8+
type hint APIs are stable and don't require extensive error handling.

Key features:
- Alternative name generation for dependency mapping
- Primitive type detection to avoid instantiation
- Constructor source analysis for attribute assignment detection
- Internal attribute constants for dependency tracking
"""

import inspect
import re
from typing import Any, Final, List, Tuple, Type

# Constants for internal attribute names
SETUP_DEPENDENCIES_ATTR: Final[str] = "_reactor_di_setup_dependencies"

_PRIMITIVE_EQUIVALENT_TYPES: Final[Tuple[Type[Any], ...]] = (
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


def get_alternative_names(name: str, default_prefix: str = "_") -> List[str]:
    """Generate alternative names based on naming conventions.

    Creates a list of name variations by removing common prefixes.
    Used for matching dependencies like '_config' to 'config'.

    Args:
        name: The base name to generate alternatives for.
        default_prefix: Default prefix to try removing (default: "_").

    Returns:
        List of alternative names to try.

    Example:
        >>> get_alternative_names("_config")
        ['config', '_config']
    """
    # Always include the original name, plus unprefixed version if applicable
    return (
        [name[len(default_prefix) :], name]
        if default_prefix and name.startswith(default_prefix)
        else [name]
    )


def is_primitive_type(attr_type: Type[Any]) -> bool:
    """Check if a type should be treated as primitive.

    Args:
        attr_type: The type to check.

    Returns:
        True if the type is primitive and should not be auto-instantiated.
    """
    return attr_type in _PRIMITIVE_EQUIVALENT_TYPES


def has_constructor_assignment(class_type: Type[Any], attr_name: str) -> bool:
    """Check if a class constructor assigns to a specific attribute.

    Uses regex to detect attribute assignments in __init__ source code.
    Handles both standard (self.attr = value) and annotated (self.attr: Type = value)
    assignment patterns. Dynamically uses the actual first parameter name.

    Args:
        class_type: The class to check.
        attr_name: The attribute name to look for in the constructor.

    Returns:
        True if the constructor assigns to the attribute, False otherwise.

    Example:
        >>> class Config:
        ...     def __init__(self):
        ...         self.timeout = 30
        >>> has_constructor_assignment(Config, "timeout")
        True
    """
    # Get the first parameter name (usually "self" but could be anything)
    init = class_type.__init__
    self = next(iter(inspect.signature(init).parameters))

    source = inspect.getsource(init)
    # Use combined regex pattern to match both assignment and type annotation
    # Matches: self.attr = value OR self.attr: Type = value
    return bool(
        re.search(rf"{re.escape(self)}\s*\.\s*{re.escape(attr_name)}\s*[=:]", source)
    )


def pure_hasattr(obj: Any, attr_name: str) -> bool:
    """Check if an attribute exists without side effects like triggering descriptors/properties."""
    try:
        if attr_name in obj.__dict__:
            return True
    except AttributeError:
        pass

    for cls in type(obj).__mro__:
        try:
            if attr_name in cls.__dict__:
                return True
        except AttributeError:
            pass

        try:
            if attr_name in cls.__slots__:  # type: ignore[attr-defined]
                return True
        except AttributeError:
            pass

    return False
