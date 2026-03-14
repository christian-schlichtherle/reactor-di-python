"""Type utilities for dependency injection and attribute resolution.

Provides type checking and analysis utilities for the Reactor DI system.
Simplified after removing unnecessary defensive programming - Python 3.9+
type hint APIs are stable and don't require extensive error handling.

Key features:
- Alternative name generation for dependency mapping
- Primitive type detection to avoid instantiation
- Constructor source analysis for attribute assignment detection
- ``lookup`` annotation marker for parent-module dependency resolution
- Internal attribute constants for dependency tracking
"""

from __future__ import annotations

import inspect
import re
from typing import Any, Final

# Constants for internal attribute names
SETUP_DEPENDENCIES_ATTR: Final[str] = "_reactor_di_setup_dependencies"
DEPENDENCY_MAP_ATTR: Final[str] = "_reactor_di_dependency_map"
MODULE_INSTANCE_ATTR: Final[str] = "_reactor_di_module_instance"
REACTOR_DI_LOCK_ATTR: Final[str] = "_reactor_di_lock"


class _LookupMarker:
    """Internal wrapper returned by ``lookup[Type]`` or ``lookup[Type, "name"]``.

    Stores the inner type and an optional *source_name* override so that
    decorators can detect, unwrap, and remap the dependency.
    """

    __slots__ = ("inner_type", "source_name")

    def __init__(self, inner_type: type[Any], source_name: str | None = None) -> None:
        self.inner_type = inner_type
        self.source_name = source_name

    def __repr__(self) -> str:
        name = getattr(self.inner_type, "__name__", repr(self.inner_type))
        if self.source_name is not None:
            return f'lookup[{name}, "{self.source_name}"]'
        return f"lookup[{name}]"


class lookup:
    """Annotation marker for dependencies resolved from a parent module.

    Usage::

        @module(CachingStrategy.NOT_THREAD_SAFE)
        class ChildModule:
            db: lookup[DatabaseConnection]              # lookup "db" on parent
            conn: lookup[DatabaseConnection, "db"]      # lookup "db" on parent, bind to "conn"
            service: MyService                          # created locally as usual

    The optional second parameter names the attribute to look up on the
    parent module.  When omitted, the annotation's own name is used.

    On a **module**, ``@module`` skips factory generation and installs a
    lightweight property so the name is visible to child-component factories.
    The actual value is injected lazily by the parent module.

    On a **component**, ``lookup`` is a no-op — the type is unwrapped and
    dependency resolution proceeds as normal.

    All other use is an error.
    """

    def __class_getitem__(cls, params: Any) -> _LookupMarker:
        if isinstance(params, tuple):
            return _LookupMarker(*params)
        return _LookupMarker(params)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("lookup cannot be subclassed")

    def __init__(self) -> None:
        raise TypeError(
            "lookup is not instantiable — use as a type annotation: lookup[Type]"
        )


def is_lookup_type(annotation: Any) -> bool:
    """Return True if *annotation* is a ``lookup[X]`` marker."""
    return isinstance(annotation, _LookupMarker)


def unwrap_lookup(annotation: Any) -> Any:
    """Unwrap ``lookup[X]`` to ``X``.  Returns *annotation* unchanged otherwise."""
    if isinstance(annotation, _LookupMarker):
        return annotation.inner_type
    return annotation


_PRIMITIVE_EQUIVALENT_TYPES: Final[tuple[type[Any], ...]] = (
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


def get_alternative_names(name: str, default_prefix: str = "_") -> list[str]:
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


def is_primitive_type(attr_type: type[Any]) -> bool:
    """Check if a type should be treated as primitive.

    Args:
        attr_type: The type to check.

    Returns:
        True if the type is primitive and should not be auto-instantiated.
    """
    return attr_type in _PRIMITIVE_EQUIVALENT_TYPES


def has_constructor_assignment(class_type: type[Any], attr_name: str) -> bool:
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

    try:
        source = inspect.getsource(init)
    except OSError:
        # Source unavailable (e.g. dataclass-generated __init__) — can't prove
        # the assignment exists, so conservatively return False.
        return False
    # Use combined regex pattern to match both assignment and type annotation
    # Matches: self.attr = value OR self.attr: Type = value
    return bool(
        re.search(rf"{re.escape(self)}\s*\.\s*{re.escape(attr_name)}\s*[=:]", source)
    )


def resolve_abstract_property_conflicts(cls: type[Any]) -> None:
    """Replace inherited abstract @properties that collide with DI annotations.

    When a class has type annotations whose names match inherited abstract
    @property methods, the property descriptor (a data descriptor) takes MRO
    priority over ``__getattr__``, preventing lazy DI resolution.  This function
    detects such collisions and installs concrete ``@property`` descriptors
    backed by ``instance.__dict__``, then removes them from
    ``__abstractmethods__`` so the class can be instantiated.

    Safe to call multiple times — skips names that are no longer abstract.
    """
    abstracts: frozenset[str] = getattr(cls, "__abstractmethods__", frozenset())
    if not abstracts:
        return

    # Gather all annotation names across the MRO
    annotations: set[str] = set()
    for klass in cls.__mro__:
        if klass is not object:
            annotations.update(getattr(klass, "__annotations__", {}))

    resolved: set[str] = set()
    for name in annotations:
        if name not in abstracts:
            continue
        # Verify the abstract method is actually a @property on a parent class
        for parent in cls.__mro__[1:]:
            if name in parent.__dict__:
                attr = parent.__dict__[name]
                if isinstance(attr, property) and getattr(
                    attr.fget, "__isabstractmethod__", False
                ):
                    _install_dict_backed_property(cls, name)
                    resolved.add(name)
                break

    if resolved:
        cls.__abstractmethods__ = abstracts - resolved


def _install_dict_backed_property(cls: type[Any], name: str) -> None:
    """Install a concrete @property on *cls* that reads/writes ``__dict__``.

    The getter checks ``__dict__`` first (fast path for already-resolved
    values).  On a miss it delegates to the class's ``__getattr__`` — which
    is typically ``_module_getattr`` installed by the ``@module`` factory —
    to perform lazy DI resolution.
    """

    def _getter(self: Any) -> Any:
        try:
            return self.__dict__[name]
        except KeyError:
            # Delegate to __getattr__ for lazy DI resolution
            ga = type(self).__dict__.get("__getattr__")
            if ga is not None:
                return ga(self, name)
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            ) from None

    def _setter(self: Any, value: Any) -> None:
        self.__dict__[name] = value

    setattr(cls, name, property(_getter, _setter))


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
