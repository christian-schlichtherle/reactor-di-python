# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A code generator for dependency injection (DI) in Python based on the mediator and factory patterns. This is a modern, production-ready Python package with comprehensive tooling.

## Development Environment

- **Python Version**: 3.9+ (minimum supported version)
- **Package Manager**: `uv` for dependency management
- **Project Layout**: Modern src-layout structure
- **Build System**: `hatchling` with `hatch-vcs` for automatic git tag versioning

## Common Commands

### Package Management
- `uv sync` - Install all dependencies (single dev group)
- `uv add <package>` - Add a new dependency
- `uv remove <package>` - Remove a dependency

### Testing
- `uv run pytest` - Run tests without coverage (fast, for development)
- `uv run pytest --cov` - Run tests with coverage and HTML/terminal/XML reports
- `uv run pytest examples/` - Run testable examples (20 tests)
- `uv run pytest -m "not slow"` - Skip slow tests

### Code Quality
- `uv run ruff check src tests examples` - Run linting (style, imports, complexity, Python idioms)
- `uv run black --check src tests examples` - Check code formatting
- `uv run black src tests examples` - Format code  
- `uv run mypy src` - Run static type checking (type safety, None checks, function signatures)

### Building and Publishing
- `uv build` - Build package for distribution
- `uv publish` - Publish to PyPI (requires trusted publishing setup)

## Project Structure

```
reactor-di-python/
├── src/reactor_di/              # Main package (src-layout)
│   ├── __init__.py             # Package initialization
│   ├── module.py               # @module decorator for DI containers
│   ├── law_of_demeter.py       # @law_of_demeter decorator for property forwarding
│   ├── caching.py              # CachingStrategy enum and thread_safe_cached_property descriptor
│   ├── type_utils.py           # Shared type checking utilities
│   └── py.typed                # Type marker for mypy
├── tests/                      # Regression and unit tests (49 tests)
│   ├── __init__.py             # Package initialization
│   ├── config.py               # Test config fixture
│   ├── database.py             # Test database fixture
│   ├── test_dataclass_law_of_demeter.py # Dataclass + stacked @law_of_demeter tests (3 tests)
│   ├── test_forward_ref.py     # TYPE_CHECKING forward reference handling
│   ├── test_law_of_demeter.py  # Law of Demeter decorator tests
│   ├── test_lazy_resolution.py # Lazy per-attribute resolution with deferred init
│   ├── test_module_integration.py # Module + law_of_demeter integration tests
│   ├── test_pure_hasattr.py    # pure_hasattr utility tests (14 tests)
│   ├── test_side_effects.py    # Side effects isolation tests
│   └── test_thread_safe.py     # Thread-safe caching strategy tests (12 tests)
├── examples/                   # Testable examples (32 tests, acts as test suite)
│   ├── __init__.py             # Package initialization
│   ├── quick_start.py          # Quick Start example as tests (4 tests)
│   ├── quick_start_advanced.py # Advanced quick start example (4 tests)
│   ├── caching_strategy.py     # Caching strategy examples (5 tests)
│   ├── custom_prefix.py        # Custom prefix examples (6 tests)
│   ├── nested_modules.py       # Nested modules and component-level lookup (10 tests)
│   ├── side_effects.py         # Side effects testing (1 test)
│   └── stacked_decorators.py   # Stacked decorators example (2 tests)
├── .github/workflows/          # CI/CD pipelines
│   ├── ci.yaml                 # Matrix testing across Python versions
│   └── publish.yaml            # PyPI deployment
└── pyproject.toml             # Modern Python configuration
```

## Architecture

This is a **code generator** for dependency injection, not a runtime DI framework. Understanding these architectural patterns is crucial for effective development:

### Code Generation Philosophy
- **Decoration-Time Property Creation**: Properties are created when classes are decorated, not when instances are created
- **Zero Runtime Overhead**: All dependency resolution happens at decoration time
- **Type Safety**: Full IDE support and type checking since all properties exist at class definition time

### Decorator Cooperation System
The decorators work together seamlessly without special configuration:
- **`@law_of_demeter`** (`law_of_demeter.py`): Creates forwarding properties for explicitly annotated attributes
- **`@module`** (`module.py`): Generates factory methods for dependency injection, recognizing properties created by `@law_of_demeter` as "already implemented"
- **`lookup`** (`type_utils.py`): Annotation marker (`lookup[Type]`) for parent-module dependency resolution — on modules, tells `@module` to skip factory generation; on components, tells `@law_of_demeter` to skip forwarding so the module factory resolves it instead
- **Validation Integration**: `@module` validates only unimplemented dependencies, allowing clean cooperation

### Type System Integration (`type_utils.py`)
Simplified utilities that enable type-safe DI across both decorators:
- **`get_alternative_names()`**: Generates name variations for dependency mapping (e.g., `_config` → `config`)
- **`has_constructor_assignment()`**: Detects attribute assignments in constructor source code
- **`is_primitive_type()`**: Identifies primitive types that shouldn't be auto-instantiated
- **`lookup`**: Annotation marker class — on modules, `lookup[Type]` tells `@module` to skip factory generation; on components, tells `@law_of_demeter` to skip forwarding so the module factory resolves it; `lookup[Type, "name"]` remaps to a different parent attribute
- **`is_lookup_type()` / `unwrap_lookup()`**: Detection and unwrapping helpers for `lookup[Type]` annotations
- **`resolve_abstract_property_conflicts()`**: Replaces inherited abstract `@property` descriptors that collide with DI annotations, installing concrete dict-backed properties so `__getattr__` DI resolution works
- **`pure_hasattr()`**: Checks attribute existence without triggering descriptors or properties
- **Internal Constants**: `DEPENDENCY_MAP_ATTR`, `MODULE_INSTANCE_ATTR` for lazy dependency resolution; `REACTOR_DI_LOCK_ATTR` for thread-safe locking; `SETUP_DEPENDENCIES_ATTR` for backward-compatible deferred setup

### Key Architectural Patterns
- **Mediator Pattern**: `@module` acts as central coordinator for all dependencies
- **Factory Pattern**: Generates `@cached_property`, `property`, or `@thread_safe_cached_property` methods for object creation
- **`lookup` on Modules and Components**: `lookup[Type]` declares dependencies resolved from the parent module — on modules it skips factory generation, on components it prevents `@law_of_demeter` forwarding so the module factory handles resolution
- **Lazy Per-Attribute Resolution**: Dependencies from `@module` are resolved individually on first access via `__getattr__`, not eagerly all at once
- **Deferred Resolution**: `_DeferredProperty` class handles runtime attribute forwarding for `@law_of_demeter`
- **Pluggable Caching**: `CachingStrategy` enum applied at decoration time
- **Safe Forward Reference Handling**: `get_type_hints()` fallback to raw `__annotations__` for `TYPE_CHECKING` imports
- **Abstract Property Conflict Resolution**: Automatically replaces inherited abstract `@property` descriptors that collide with DI annotations
- **Simplified Error Handling**: Removed unnecessary defensive programming for Python 3.9+ stable APIs

## Testing Strategy

- **Coverage Achievement**: 90% test coverage requirement (focused on realistic scenarios)
- **Framework**: pytest with pytest-cov
- **Matrix Testing**: Python 3.9, 3.10, 3.11, 3.12, 3.13, 3.14
- **Test Architecture**:
  - **Unit/Regression Tests**: Bug regression tests and utility tests in `tests/` (49 tests)
  - **Example Tests**: Real-world usage patterns as executable tests in `examples/` (32 tests)
  - **Streamlined Configuration**: Minimal pytest configuration for essential functionality
- **Test Quality**: Prioritize meaningful assertions over empty coverage metrics
- **Realistic Testing**: Remove unrealistic defensive code rather than mock impossible scenarios

### Development Configuration
- **Single Dependency Group**: Combined dev tools for simplified management
- **Coverage Testing**: Use `--cov` flag to enable coverage when needed
- **Coverage Threshold**: Set to 90% (fail_under = 90) when coverage is enabled
- **Essential Tools Only**: 
  - **black**: Code formatting
  - **mypy**: Static type checking  
  - **pytest-cov**: Test coverage
  - **pytest**: Testing framework
  - **ruff**: Linting and style checks

## CI/CD Pipeline

- **GitHub Actions**: Matrix testing across Python versions
- **Trusted Publishing**: Secure PyPI deployment without API keys
- **Quality Gates**: Tests, linting (ruff), formatting (black), and type checking (mypy) must pass
- **Automatic Deployment**: Triggered on git tags (v*)

## Development Workflow

1. Make changes in `src/reactor_di/`
2. Add/update tests in `tests/` and examples in `examples/`
3. Run quality checks: `uv run pytest --cov && uv run ruff check src tests examples && uv run black --check src tests examples && uv run mypy src`
4. Update documentation if needed
5. Commit and push (CI will validate)

## Key Development Insights

### Understanding Decorator Interaction
- Both decorators use simplified type checking from `type_utils.py`
- `@law_of_demeter` creates forwarding properties using `_DeferredProperty` for runtime resolution
- `@module` skips attributes already handled by `@law_of_demeter` through `hasattr` checks
- Decorator cooperation happens naturally without complex validation logic

### Architectural Decisions
- **Explicit Annotations Required**: Only annotated attributes are forwarded/synthesized
- **Decoration-Time Creation**: Properties exist at class definition time for better IDE support
- **Simplified Validation**: Direct type checking without excessive error handling
- **Greedy vs Reluctant**: `@module` raises errors for unsatisfied dependencies, `@law_of_demeter` silently skips

## Key Features

- Modern Python packaging with hatchling build backend
- Automatic versioning from git tags via hatch-vcs
- Comprehensive testing with coverage enforcement
- Automated CI/CD with GitHub Actions
- Static type checking with mypy for type safety and None checks
- Code quality with ruff (linting) and black (formatting) - configured for Python 3.9+
- Secure PyPI deployment with trusted publishing

## Recent Updates

### Feature: `lookup` Annotation Marker (Latest)
- Added `lookup` annotation marker in `type_utils.py` for parent-module dependency resolution
- `lookup[Type]` on a **module** annotation tells `@module` to skip factory generation and install a dict-backed property instead
- `lookup[Type]` on a **component** annotation tells `@law_of_demeter` to skip forwarding — the parent module's factory resolves it through the dependency-map mechanism
- `lookup[Type, "name"]` allows remapping: look up `"name"` on the parent module but bind locally under the annotation's own name (works on both modules and components)
- The actual value is injected lazily by the parent module through the existing dependency-map mechanism
- `_install_dict_backed_property` makes lookup names visible to `pure_hasattr` so child-component factories can build dependency maps
- Modules can be nested to arbitrary depth — lookup chains through parent → child → grandchild
- Added `_LookupMarker` internal class (with `inner_type` and optional `source_name`), `is_lookup_type()` and `unwrap_lookup()` helpers
- `@law_of_demeter` imports `is_lookup_type` and skips `lookup`-annotated attributes in its processing loop
- Exported `lookup` from `reactor_di.__init__`
- Added 10 example tests in `examples/nested_modules.py` covering parent injection, component usage, sibling sharing, base_ref unwrapping, deep nesting, renamed lookup, renamed lookup feeding components, component-level lookup skipping forwarding, component-level renamed lookup, and end-to-end component lookup

### Bug Fix: Abstract Property Conflicts with DI Resolution
- Fixed `TypeError` / shadowed DI when a component class inherits abstract `@property` methods from an ABC that collide with DI annotation names
- `resolve_abstract_property_conflicts()` in `type_utils.py` detects collisions and installs concrete `@property` descriptors backed by `instance.__dict__`, then removes them from `__abstractmethods__`
- `_install_dict_backed_property()` creates getter (fast-path `__dict__` lookup, fallback to `__getattr__` for lazy DI) and setter
- Called by both `@law_of_demeter` (before processing annotations) and `@module` factory (before creating dependencies) — idempotent, skips already-resolved names
- Added 3 regression tests in `tests/test_module_integration.py` covering DI resolution, `@law_of_demeter` forwarding, and direct instantiation with abstract property conflicts

### Feature: Thread-Safe Caching Strategy
- Added `CachingStrategy.THREAD_SAFE` for singleton components with thread-safe guarantees
- `thread_safe_cached_property` descriptor (in `caching.py`) uses double-checked locking with per-instance, per-attribute locks
- Fast path (already cached) is a single `__dict__` lookup with no locking overhead
- Thread-safe `_module_getattr`: lazy dependency resolution acquires a per-instance lock (`REACTOR_DI_LOCK_ATTR`) when resolving dependencies for `THREAD_SAFE` modules
- Only `THREAD_SAFE` modules pay the locking cost — `NOT_THREAD_SAFE` and `DISABLED` are unchanged
- Added `REACTOR_DI_LOCK_ATTR` constant in `type_utils.py` for the per-instance lock attribute name
- Added 7 regression tests in `tests/test_thread_safe.py` covering concurrent access, `_module_getattr` thread safety, mixed strategies, and `@law_of_demeter` integration
- Added 2 example tests in `examples/caching_strategy.py` demonstrating thread-safe caching and concurrent access

### Bug Fix: TYPE_CHECKING Forward Reference Handling
- Fixed `NameError` when component classes use `if TYPE_CHECKING:` imports to avoid circular dependencies
- The module factory's `get_type_hints()` call now falls back to raw `__annotations__` from the MRO when forward references can't be resolved at runtime
- This is safe because the factory only needs annotation *names* (not resolved types) for dependency mapping
- Common pattern: `from __future__ import annotations` + `if TYPE_CHECKING: from other_module import SomeClass`
- Added regression test in `tests/test_forward_ref.py` reproducing the `TYPE_CHECKING` forward reference pattern

### Bug Fix: Lazy Per-Attribute Dependency Resolution
- Replaced eager all-at-once `setup_dependencies()` closure with lazy per-attribute resolution in `module.py`
- Dependencies are now stored as a map (`DEPENDENCY_MAP_ATTR` + `MODULE_INSTANCE_ATTR`) on the component instance and resolved individually via `__getattr__` on first access
- This fixes failures when module `cached_property` methods depend on deferred initialization (e.g., attributes set in `__aenter__` for async context managers)
- Accessing one dependency (e.g., `_config`) no longer triggers resolution of unrelated dependencies (e.g., `_api`, `_namespace`)
- Failed resolution attempts preserve the map entry for retry after deferred init completes
- Optimized `_DeferredProperty.__get__` to check `instance.__dict__` directly instead of `hasattr`, avoiding unnecessary `__getattr__` triggers
- Added 3 regression tests for lazy resolution with deferred initialization patterns

### Bug Fixes: Pydantic/Annotation-Only Config Compatibility
- Fixed `_can_resolve_attribute` in `law_of_demeter.py` to check `get_type_hints(base_type)` for annotation-only fields (e.g., Pydantic BaseSettings/BaseModel)
- Replaced class-level `__getattribute__` patching in `module.py` with a safe `__getattr__` fallback (`_module_getattr`), eliminating class pollution across instances
- `__getattr__` is only called when normal attribute lookup fails, making it safe and idempotent
- Added `pure_hasattr()` utility in `type_utils.py` to check attribute existence without triggering descriptors or properties
- Added regression tests in `tests/` covering annotation-only config forwarding, class pollution prevention, and `pure_hasattr` behavior

### Code Simplification
- Removed complex parent resolution logic from `@law_of_demeter`
- Made `DeferredProperty` private (`_DeferredProperty`) to indicate internal use
- Fixed bug in `get_alternative_names` using `append` instead of `extend`
- Simplified module.py with clearer error messages and removed unused imports
- Streamlined type checking by removing unnecessary try-except blocks
- Uses walrus operator (`:=`) for cleaner conditionals (Python 3.8+)
- Uses PEP 585 built-in generics (`list`, `tuple`, `type`) and PEP 604 union syntax (`X | Y`) with `from __future__ import annotations` for Python 3.9 compatibility

### Testing Infrastructure
- Single dependency group combining dev and test tools for simplicity
- Coverage reports (HTML, terminal, XML) generated when `--cov` flag is used
- Coverage threshold set to 90% for higher quality standards
- Minimal pytest configuration focused on essential functionality
- Streamlined dependency footprint with only essential tools

### Build System (Latest)
- Switched from setuptools to hatchling for modern, faster builds
- Automatic versioning from git tags using hatch-vcs
- No version files needed - version determined at build time from git
- Cleaner configuration with better defaults

### Tool Clarification
- **ruff**: Fast linter for code style, imports, complexity, and Python idioms
- **mypy**: Static type checker for type safety, None checks, and function signatures
- **black**: Code formatter for consistent code style
- Both ruff and mypy are needed as they serve complementary purposes