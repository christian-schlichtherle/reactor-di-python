# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A code generator for dependency injection (DI) in Python based on the mediator and factory patterns. This is a modern, production-ready Python package with comprehensive tooling.

## Development Environment

- **Python Version**: 3.9 for development (requires 3.8+ due to `@cached_property`)
- **Package Manager**: `uv` for dependency management
- **Project Layout**: Modern src-layout structure
- **Build System**: `hatchling` with `pyproject.toml`

## Common Commands

### Package Management
- `uv sync --all-groups` - Install all dependencies including dev/test/docs
- `uv add <package>` - Add a new dependency (note: adds setuptools for PyCharm compatibility)
- `uv remove <package>` - Remove a dependency

### Testing
- `uv run pytest` - Run tests without coverage (fast, for development)
- `uv run pytest --cov` - Run tests with coverage and HTML/terminal reports
- `uv run pytest examples/` - Run testable examples (20 tests)
- `uv run pytest -m "not slow"` - Skip slow tests

### Code Quality
- `uv run ruff check src tests examples` - Run linting (configured for Python 3.8+ compatibility)
- `uv run black --check src tests examples` - Check code formatting
- `uv run black src tests examples` - Format code
- `uv run mypy src` - Run type checking

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
│   ├── caching.py              # CachingStrategy enum for component caching
│   ├── type_utils.py           # Shared type checking utilities
│   └── py.typed                # Type marker for mypy
├── tests/                      # Test suite directory (currently empty - tests in examples/)
│   └── __init__.py             # Package initialization
├── examples/                   # Testable examples (20 tests, acts as test suite)
│   ├── __init__.py             # Package initialization
│   ├── quick_start.py          # Quick Start example as tests (4 tests)
│   ├── quick_start_advanced.py # Advanced quick start example (4 tests)
│   ├── caching_strategy.py     # Caching strategy examples (3 tests)
│   ├── custom_prefix.py        # Custom prefix examples (6 tests)
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
The two decorators work together seamlessly without special configuration:
- **`@law_of_demeter`** (`law_of_demeter.py`): Creates forwarding properties for explicitly annotated attributes
- **`@module`** (`module.py`): Generates factory methods for dependency injection, recognizing properties created by `@law_of_demeter` as "already implemented"
- **Validation Integration**: `@module` validates only unimplemented dependencies, allowing clean cooperation

### Type System Integration (`type_utils.py`)
Simplified utilities that enable type-safe DI across both decorators:
- **`get_alternative_names()`**: Generates name variations for dependency mapping (e.g., `_config` → `config`)
- **`has_constructor_assignment()`**: Detects attribute assignments in constructor source code
- **`is_primitive_type()`**: Identifies primitive types that shouldn't be auto-instantiated
- **Internal Constants**: `DEPENDENCY_MAP_ATTR`, `PARENT_INSTANCE_ATTR`, `SETUP_DEPENDENCIES_ATTR` for tracking

### Key Architectural Patterns
- **Mediator Pattern**: `@module` acts as central coordinator for all dependencies
- **Factory Pattern**: Generates `@cached_property` or `property` methods for object creation
- **Deferred Resolution**: `_DeferredProperty` class handles runtime attribute forwarding
- **Pluggable Caching**: `CachingStrategy` enum applied at decoration time
- **Simplified Error Handling**: Removed unnecessary defensive programming for Python 3.8+ stable APIs

## Testing Strategy

- **Coverage Achievement**: 90% test coverage requirement (focused on realistic scenarios)
- **Framework**: pytest with pytest-cov
- **Matrix Testing**: Python 3.8, 3.9, 3.10, 3.11, 3.12, 3.13
- **Test Architecture**: 
  - **Example Tests**: Real-world usage patterns as executable tests in `examples/`
  - **Coverage Separation**: Coverage config in `pytest-cov.ini` for CI/CD, clean config for PyCharm debugging
- **Test Quality**: Prioritize meaningful assertions over empty coverage metrics
- **Realistic Testing**: Remove unrealistic defensive code rather than mock impossible scenarios

### PyCharm Testing Configuration
- **Default**: PyCharm runs tests without coverage for fast feedback and debugging
- **Coverage Testing**: Use `--cov` flag to enable coverage when needed
- **Coverage Threshold**: Set to 90% (fail_under = 90) when coverage is enabled
- **Setuptools Requirement**: Added to dev dependencies for PyCharm's pytest runner compatibility

## CI/CD Pipeline

- **GitHub Actions**: Matrix testing across Python versions
- **Trusted Publishing**: Secure PyPI deployment without API keys
- **Quality Gates**: Tests, linting, type checking must pass
- **Automatic Deployment**: Triggered on git tags (v*)

## Development Workflow

1. Make changes in `src/reactor_di/`
2. Add/update tests in `tests/` and examples in `examples/`
3. Run quality checks: `uv run pytest && uv run ruff check src tests examples && uv run mypy src`
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

- Modern Python packaging with pyproject.toml
- Comprehensive testing with coverage enforcement
- Automated CI/CD with GitHub Actions
- Type safety with mypy
- Code quality with ruff and black (configured for Python 3.8+ compatibility)
- Secure PyPI deployment with trusted publishing

## Recent Updates

### Code Simplification (Latest)
- Removed complex parent resolution logic from `@law_of_demeter`
- Made `DeferredProperty` private (`_DeferredProperty`) to indicate internal use
- Fixed bug in `get_alternative_names` using `append` instead of `extend`
- Simplified module.py with clearer error messages and removed unused imports
- Streamlined type checking by removing unnecessary try-except blocks
- Uses walrus operator (`:=`) for cleaner conditionals (Python 3.8+)

### Python 3.8 Compatibility
- Added `from __future__ import annotations` to support modern type syntax
- Disabled ruff rules UP006 and UP007 that require Python 3.9+ syntax
- Maintained use of `Type[Any]` and `Union[...]` for broader compatibility

### Testing Infrastructure
- Unified configuration in `pyproject.toml` with coverage as opt-in via `--cov`
- Coverage reports (HTML and terminal) generated when `--cov` flag is used
- Coverage threshold set to 90% for higher quality standards
- Optimized for fast development cycles with coverage disabled by default
- Added setuptools to dev dependencies for PyCharm's pytest runner