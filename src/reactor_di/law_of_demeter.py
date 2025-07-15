"""Law of Demeter decorator for creating forwarding properties.

This module provides the @law_of_demeter decorator that creates forwarding properties
for explicitly annotated attributes, helping maintain the Law of Demeter principle
in object-oriented design.

The decorator uses decoration-time property creation with selective annotation processing,
ensuring that only explicitly declared attributes are forwarded from a base reference.
It searches the entire inheritance hierarchy (MRO) for annotations and abstract attributes,
enabling proper support for complex class hierarchies.

Requires Python 3.8+

Key Features:
- Explicit annotation-driven property forwarding
- Full inheritance hierarchy (MRO) search for annotations and abstract attributes
- Type-safe validation with compatibility checking
- Natural inheritance support for complex class hierarchies
- Zero runtime introspection overhead
- Seamless integration with @module decorator from module.py

Integration with Reactor DI:
The @law_of_demeter decorator works seamlessly with @module from module.py.
When @law_of_demeter creates forwarding properties, @module recognizes them as
implemented dependencies during validation, enabling clean cooperation between
decorators without any special configuration.

Example:
    @law_of_demeter('config')
    class Controller:
        def __init__(self, config):
            self.config = config

        _timeout: int      # Creates forwarding property
        _is_dry_run: bool  # Creates forwarding property

    controller = Controller(config)
    controller._timeout    # → config.timeout
    controller._is_dry_run # → config.is_dry_run

For detailed usage examples and advanced patterns, see the law_of_demeter function docstring.
"""

import inspect
import re
from typing import Any, Callable, Type, get_type_hints

from .type_utils import (
    get_all_type_hints,
    is_type_compatible,
    needs_implementation,
    safe_get_type_hints,
)


def _can_resolve_annotation(
    cls: Type[Any], base_ref: str, target_attr_name: str, source_type: Type[Any]
) -> bool:
    """Check if an annotation can be resolved through the base reference.

    This implements flexible validation:
    1. base_ref type can be from class annotation or constructor parameter
    2. target_attr_name must be public (not start with _)
    3. target type must have the attribute/annotation
    4. Types must be compatible

    Args:
        cls: The class being decorated
        base_ref: The base reference name (e.g., "_config")
        target_attr_name: The attribute name to resolve (e.g., "timeout")
        source_type: The expected type of the annotation

    Returns:
        True if the annotation can be resolved and types are compatible

    Raises:
        ValueError: If base_ref type annotation is missing
        TypeError: If types are incompatible
    """
    # Try to find base_ref type annotation in class hierarchy or constructor
    cls_annotations = get_all_type_hints(cls)
    target_type = cls_annotations.get(base_ref)

    # If not found in class annotations, check constructor parameters
    if target_type is None and hasattr(cls, "__init__"):
        try:
            init_annotations = get_type_hints(cls.__init__)
            target_type = init_annotations.get(base_ref)

            # If base_ref starts with underscore, also try without underscore
            if target_type is None and base_ref.startswith("_"):
                constructor_param = base_ref[1:]  # Remove leading underscore
                target_type = init_annotations.get(constructor_param)
        except (NameError, AttributeError, TypeError):
            pass

    # If no type annotation found, allow property creation without validation
    # This provides backwards compatibility while encouraging type annotations
    if target_type is None:
        return True  # Skip validation, but allow property creation

    # If type annotation is 'object', allow property creation without validation
    # 'object' is too generic to validate against meaningfully
    if target_type is object:
        return True

    # Target member MUST be public
    if target_attr_name.startswith("_"):
        return False

    # Check if target type has this member (annotation or attribute)
    has_attr = hasattr(target_type, target_attr_name)
    target_annotations = safe_get_type_hints(target_type)
    has_annotation = target_attr_name in target_annotations

    if not (has_attr or has_annotation):
        # Try to check if the attribute is set in the constructor
        if inspect.isclass(target_type) and hasattr(target_type, "__init__"):
            try:
                init_source = inspect.getsource(target_type.__init__)
                pattern = rf"\bself\.{re.escape(target_attr_name)}\b"
                if re.search(pattern, init_source):
                    return True
            except (OSError, TypeError):
                pass

        # If source code parsing fails, try to create a test instance to check for runtime attributes
        # This is a fallback for when source code is not available
        try:
            # Try to create a minimal test instance
            # This is not ideal but necessary for some dynamic scenarios
            test_instance = target_type()
            if hasattr(test_instance, target_attr_name):
                return True
        except Exception:
            # If instance creation fails, we can't determine if the attribute exists
            pass

        # If the target type doesn't have this attribute, this decorator cannot handle it
        # Let another decorator handle it if it can resolve the dependency
        return False

    # Type compatibility check
    if has_annotation:
        target_member_type = target_annotations[target_attr_name]
        if not is_type_compatible(
            provided_type=target_member_type, required_type=source_type
        ):
            raise TypeError(
                f"Cannot forward {base_ref}.{target_attr_name}: {target_member_type} "
                f"to {cls.__name__}.{target_attr_name}: {source_type} - types incompatible"
            )

    return True


def _should_handle_annotation(annotated_name: str, prefix: str) -> bool:
    """Check if this decorator instance should handle the given annotation.

    Args:
        annotated_name: The annotation name to check
        prefix: The prefix for this decorator instance

    Returns:
        True if this decorator should handle the annotation
    """
    if prefix == "":
        # Empty prefix: only handle public annotations (no underscore)
        return not annotated_name.startswith("_")
    # Non-empty prefix: handle annotations starting with this prefix
    return annotated_name.startswith(prefix)


def law_of_demeter(
    base_ref: str,
    *,
    prefix: str = "_",
) -> Callable[[Type[Any]], Type[Any]]:
    """
    Class decorator that creates forwarding properties for explicitly annotated
    attributes, helping maintain the Law of Demeter principle.

    This decorator reduces property chains from `self.base.property` to
    `self.{prefix}property` by forwarding only the attributes you explicitly
    annotate in your class.

    IMPORTANT: Uses decoration-time property creation - properties are
    created immediately when the class is decorated and inherited naturally.

    Args:
        base_ref: Name of the attribute/reference to forward from
        prefix: Prefix to add to forwarded property names (default: '_')

    Basic Usage:
        @law_of_demeter('config')
        class Controller:
            def __init__(self, config):
                self.config = config

            # Only these annotated attributes will be forwarded
            _timeout: int
            _is_dry_run: bool
            # config.other_attr won't be forwarded (not annotated)

        controller = Controller(config)
        controller._timeout    # → config.timeout
        controller._is_dry_run # → config.is_dry_run

    Child classes inherit properties automatically:
        class ArgoCDController(Controller):
            # Inherits _timeout and _is_dry_run properties automatically!
            pass  # No need to repeat annotations

    Custom Prefixes:
        # Custom prefix
        @law_of_demeter('config', prefix='cfg_')
        class PrefixController:
            def __init__(self, config):
                self.config = config

            cfg_timeout: int
            cfg_is_dry_run: bool

        # No prefix (direct forwarding)
        @law_of_demeter('config', prefix='')
        class DirectController:
            def __init__(self, config):
                self.config = config

            timeout: int
            is_dry_run: bool

    Stacked Decorators with Auto-Setup:
        @law_of_demeter('_config')  # Sets up: self._timeout = self._config.timeout
        @law_of_demeter('_module')  # Sets up: self._config = self._module.config
        class ResourceController:
            def __init__(self, module):
                self._module = module
                # decorator automatically sets up: self._config = module.config

            # From _config
            _timeout: int
            _is_dry_run: bool

            # From _module
            _api: API
            _config: Config
            _namespace: str

    Advanced Features:
        # Works with Pydantic models and instance attributes
        class PydanticConfig(BaseModel):
            timeout: int = 300
            is_dry_run: bool = True

        @law_of_demeter('config')
        class PydanticController:
            def __init__(self, config: PydanticConfig):
                self.config = config

            _timeout: int      # Forwards Pydantic field
            _is_dry_run: bool  # Forwards Pydantic field

    Type Safety & IDE Support:
        The explicit annotations provide excellent IDE autocomplete and type checking:

        @law_of_demeter('config')
        class TypedController:
            def __init__(self, config):
                self.config = config

            _timeout: int        # IDE knows this is int
            _is_dry_run: bool    # IDE knows this is bool

    Explicit Annotation Requirement:
        The decorator only forwards properties that are explicitly annotated:

        @law_of_demeter('config')
        class Controller:
            def __init__(self, config):
                self.config = config

            _timeout: int        # Will be forwarded from config.timeout
            _debug: bool         # Will be forwarded from config.debug
            # config.other_attr  # Will NOT be forwarded (not annotated)

        This ensures predictable behavior and prevents surprise attribute forwarding.


    Side Effect Guarantees:
        - Zero property calls during object initialization
        - Properties only accessed when explicitly requested
        - Exact call chain: controller._prop → controller._module.config.prop
        - No side effects during introspection or inheritance
        - Child classes inherit with zero overhead

    Performance & Benefits:
        - Lightning-fast object creation - properties created at decoration time
        - Natural inheritance - child classes get properties automatically
        - Zero runtime introspection - all properties exist immediately
        - Explicit declaration prevents surprise attribute forwarding
        - Clean child classes - no repeated annotations needed
        - Optimal call chains - direct forwarding with minimal overhead

    Forwarding Scope:
        - Only forwards explicitly annotated attributes
        - Supports @property and instance attributes (Pydantic fields)
        - Properties are created at class decoration time
        - Child classes inherit properties via normal Python inheritance
        - Stacked decorators automatically resolve to the correct base object
    """

    def decorator(cls: Type[Any]) -> Type[Any]:

        def create_forwarding_property(attr_name: str) -> property:
            """Create a forwarding property for a given attribute name."""

            def getter(self: Any) -> Any:
                # Direct forwarding from base_ref
                base_obj = getattr(self, base_ref)
                return getattr(base_obj, attr_name)

            getter.__doc__ = f"Forwarded property from {base_ref}.{attr_name}"
            getter.__name__ = prefix + attr_name

            # Simple property forwarding
            return property(getter)

        # Create properties immediately at decoration time based on annotations
        # Use get_all_type_hints to include annotations from superclasses
        annotations = get_all_type_hints(cls)

        for annotated_name, annotated_type in annotations.items():
            # Check if this decorator instance should handle this annotation
            if not _should_handle_annotation(annotated_name, prefix):
                continue

            # Only implement annotations that need implementation
            if not needs_implementation(cls, annotated_name):
                continue

            # Extract the target attribute name (remove prefix)
            target_attr_name = annotated_name[len(prefix) :]

            # Skip the base reference itself - it should be injected by other means
            if annotated_name == base_ref:
                continue

            # Check if we can resolve this annotation through the base reference
            if not _can_resolve_annotation(
                cls, base_ref, target_attr_name, annotated_type
            ):
                continue  # Skip this annotation, let other decorators handle it

            # Create the forwarding property
            prop = create_forwarding_property(target_attr_name)
            setattr(cls, annotated_name, prop)

        return cls

    return decorator
