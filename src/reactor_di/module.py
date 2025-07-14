"""Module decorator for type-safe dependency injection through controlled component composition.

This module provides the @module decorator that acts like a chemical reactor, composing
working applications from abstract component ingredients through controlled reactions.

Like a chemical reactor, the module provides controlled conditions where:
1. Component ingredients (both ABC and non-ABC classes) are combined safely
2. Dependencies react under type-safe validation
3. Complete working implementations are synthesized on-demand
4. Full inheritance hierarchy is searched for dependencies and abstract attributes

The decorator supports concrete classes with unimplemented dependencies, not just
abstract base classes. It uses get_all_type_hints() and systematic MRO traversal
to discover dependencies and abstract attributes from the entire inheritance chain.

Requires Python 3.8+ (uses functools.cached_property)

INTEGRATION: Works seamlessly with @law_of_demeter decorator from law_of_demeter.py.
The @law_of_demeter decorator creates forwarding properties that @module recognizes as
implemented dependencies during validation, enabling clean cooperation between decorators.

Example usage:

    @module
    class AppReactor:
        # These ingredient annotations trigger controlled composition reactions
        config: Config      # Non-ABC class - directly instantiated
        database: Database  # ABC component - automatically implemented
        service: Service    # ABC component - automatically implemented

    class Service(ABC):  # Pure ingredient interface - cannot instantiate directly
        _config: Config     # Ingredient binds to reactor.config
        _database: Database # Ingredient binds to reactor.database

    # Reactor synthesis: ingredients combine to form working implementation
    reactor = AppReactor()  # No parameters needed - all dependencies self-provisioned
    service = reactor.service  # Synthesized complete Service implementation!
"""

import inspect
from functools import cached_property
from typing import Any, Callable, Set, Union

from .caching import CachingStrategy
from .type_utils import (
    get_all_type_hints,
    is_type_compatible,
    needs_implementation,
    safe_get_type_hints,
)


def _needs_synthesis(cls: Any) -> bool:
    """Check if a class needs dependency injection synthesis.

    Returns True if the class has unimplemented dependencies that require synthesis.
    This applies to both ABC and non-ABC classes. Searches the entire inheritance
    hierarchy for abstract methods and unimplemented annotations.

    Returns False if the class can be directly instantiated (all dependencies implemented).
    """
    if not inspect.isclass(cls):
        return False

    # Check if it has abstract methods (definitely needs synthesis)
    abstract_methods: Set[str] = getattr(cls, "__abstractmethods__", set())
    if len(abstract_methods) > 0:
        return True

    # Check if any annotations need implementation (including from superclasses)
    annotations = get_all_type_hints(cls)
    return any(needs_implementation(cls, attr_name) for attr_name in annotations)


def _validate_component_dependencies(module_cls: type, component_type: type) -> None:
    """Validate that module provides all ingredients needed by component.

    Args:
        module_cls: The module class being decorated
        component_type: The ABC component type to validate

    Raises:
        TypeError: If ingredients are missing or incompatible for the reaction
    """
    module_annotations = safe_get_type_hints(module_cls)
    component_deps = get_all_type_hints(component_type)

    for dep_name, dep_type in component_deps.items():
        # Skip validation for dependencies already implemented as properties by other decorators
        # (e.g., @law_of_demeter may have already created forwarding properties)
        # Also skip dependencies that don't need implementation (i.e., already implemented elsewhere)
        if not needs_implementation(component_type, dep_name):
            continue  # Already implemented, no need to validate module provides it

        # Note: We don't skip underscore dependencies anymore - we check if they were
        # actually implemented by @law_of_demeter. The needs_implementation check above
        # will skip dependencies that were actually implemented.

        # For validation, strip leading underscore to find the module attribute
        module_attr_name = dep_name.lstrip("_")

        # Check if module provides this dependency via annotation, property, or cached_property
        is_provided = (
            module_attr_name in module_annotations  # Type annotation
            or hasattr(module_cls, module_attr_name)  # Property/method/cached_property
        )

        if not is_provided:
            raise TypeError(
                f"{component_type.__name__} requires dependency '{dep_name}: {dep_type}' "
                f"but {module_cls.__name__} doesn't provide '{module_attr_name}'"
            )

        # Check type compatibility if module has type annotation
        if module_attr_name in module_annotations:
            provided_type = module_annotations[module_attr_name]
            if not is_type_compatible(
                provided_type=provided_type, required_type=dep_type
            ):
                raise TypeError(
                    f"{component_type.__name__} requires '{dep_name}: {dep_type}' "
                    f"but {module_cls.__name__}.{module_attr_name} provides '{provided_type}'. "
                    f"Types are not compatible."
                )

        # For properties/methods without type annotations, we can't validate the type
        # This is a limitation, but better than not checking at all


def _create_direct_factory_func(
    name: str, component_type: type
) -> Callable[[Any], Any]:
    """Create a factory function that directly instantiates a non-ABC class.

    Args:
        name: The attribute name for the synthesis method
        component_type: The class type to synthesize directly

    Returns:
        A factory function that synthesizes instances with zero parameters
    """

    def factory(_: Any) -> Any:
        # Direct instantiation with no parameters (like Config())
        return component_type()

    factory.__name__ = name
    factory.__doc__ = f"Create {name.replace('_', ' ')} instance."
    factory.__annotations__ = {"return": component_type}

    return factory


def _create_bound_factory_func(name: str, component_type: type) -> Callable[[Any], Any]:
    """Create a factory function that returns a composed component implementation.

    Args:
        name: The attribute name for the synthesis method
        component_type: The ABC component type to compose from ingredients

    Returns:
        A factory function that synthesizes complete component implementations
    """

    def factory(self: Any) -> Any:
        # Capture module instance in closure
        module_instance = self

        # Get component ingredient requirements from entire inheritance hierarchy
        component_deps = get_all_type_hints(component_type)

        # Create a synthesized class definition (runs only once due to module-level caching!)
        class SynthesizedComponent(component_type):
            pass

        # Generate binding properties for each ingredient
        for ingredient_name, ingredient_type in component_deps.items():
            # Skip dependencies already implemented by other decorators (e.g., @law_of_demeter)
            if hasattr(component_type, ingredient_name):
                continue  # Already implemented, don't override

            def make_ingredient_binder(
                attr_name: str, module_attr_name: str, bound_ingredient_type: type
            ) -> property:
                def ingredient_binder(_: Any) -> Any:
                    return getattr(module_instance, module_attr_name)

                ingredient_binder.__name__ = attr_name
                ingredient_binder.__doc__ = (
                    f"Get {module_attr_name.replace('_', ' ')} ingredient from module."
                )
                ingredient_binder.__annotations__ = {"return": bound_ingredient_type}

                return property(ingredient_binder)

            # Determine module attribute name (strip leading underscore if present)
            module_attr_name = ingredient_name.lstrip("_")
            setattr(
                SynthesizedComponent,
                ingredient_name,
                make_ingredient_binder(
                    ingredient_name, module_attr_name, ingredient_type
                ),
            )

        # Set proper naming for debugging
        SynthesizedComponent.__name__ = component_type.__name__
        SynthesizedComponent.__qualname__ = (
            f"{module_instance.__class__.__name__}.{component_type.__name__}"
        )

        # Synthesize and return (caching controlled by module-level strategy)
        return SynthesizedComponent()

    factory.__name__ = name
    factory.__doc__ = f"Synthesize composed {name.replace('_', ' ')} implementation."
    factory.__annotations__ = {"return": component_type}

    return factory


def module(
    cls_or_strategy: Union[type, CachingStrategy, None] = None, /
) -> Union[type, Callable[[type], type]]:
    """Reactor DI decorator for dependency injection module/container classes.

    Scans class annotations and automatically implements ABC classes through
    controlled component composition. Acts like a chemical reactor where:
    - Ingredient compatibility is validated at decoration time
    - Pure ABCs (with abstract methods) are synthesized into implementations
    - Concrete classes (including ABC subclasses) are directly instantiated
    - Complete working implementations are produced on-demand

    Usage:
        @module                                    # Legacy (DISABLED default)
        @module()                                  # Explicit default (DISABLED)
        @module(CachingStrategy.NOT_THREAD_SAFE)   # Explicit strategy

    Example:
        @module(CachingStrategy.NOT_THREAD_SAFE)
        class AppReactor:
            service: MyService  # ABC components are automatically implemented
            config: Config     # Non-ABC classes are directly instantiated

        class MyService(ABC):  # Pure ingredient interface - cannot instantiate directly
            _config: Config

        # Reactor synthesis:
        reactor = AppReactor()
        service = reactor.service  # Returns synthesized MyService implementation

    Args:
        cls_or_strategy: Either the class to decorate (legacy) or caching strategy

    Returns:
        The decorated class with generated synthesis methods
    """

    def decorator(cls: type, strategy: CachingStrategy) -> type:
        """Internal decorator that performs DI synthesis with given strategy"""
        # Get type annotations, handling forward references
        annotations = safe_get_type_hints(cls)

        # Generate factory methods for each annotation
        for attr_name, attr_type in annotations.items():
            # Only implement annotations that need implementation
            if not needs_implementation(cls, attr_name):
                continue  # Skip already implemented attributes

            # Resolve actual type from string annotation if needed
            actual_type = attr_type
            if isinstance(attr_type, str):
                try:
                    # Try to resolve from module's globals
                    frame = inspect.currentframe()
                    if frame and frame.f_back:
                        module_globals = frame.f_back.f_globals
                        actual_type = module_globals.get(attr_type, attr_type)
                except (AttributeError, KeyError):
                    actual_type = attr_type

            # Create factory function
            if _needs_synthesis(actual_type):
                # Validate ingredient compatibility at decoration time (reaction safety!)
                _validate_component_dependencies(cls, actual_type)
                factory_func = _create_bound_factory_func(attr_name, actual_type)
            else:
                # For classes that can be directly instantiated (like Config)
                factory_func = _create_direct_factory_func(attr_name, actual_type)

            # Apply caching strategy at decoration time
            prop: Union[property, cached_property]
            if strategy == CachingStrategy.DISABLED:
                prop = property(factory_func)
            else:  # CachingStrategy.NOT_THREAD_SAFE
                prop = cached_property(factory_func)
                # Only cached_property has __set_name__
                prop.__set_name__(cls, attr_name)

            setattr(cls, attr_name, prop)

        return cls

    # Handle different usage patterns - ordered from specific to general
    if isinstance(cls_or_strategy, CachingStrategy):
        # @module(CachingStrategy.NOT_THREAD_SAFE) - enum instance
        return lambda cls: decorator(cls, cls_or_strategy)
    if isinstance(cls_or_strategy, type):
        # @module - legacy, class being decorated
        return decorator(cls_or_strategy, CachingStrategy.DISABLED)
    if cls_or_strategy is None:
        # @module() - explicit parentheses
        return lambda cls: decorator(cls, CachingStrategy.DISABLED)
    raise TypeError(f"Invalid argument to @module: {cls_or_strategy}")
