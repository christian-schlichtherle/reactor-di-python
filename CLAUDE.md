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
- `./scripts/test-with-coverage.sh` - Run all tests with coverage (20 tests from examples/)
- `uv run pytest` - Run tests without coverage (useful for debugging)
- `uv run pytest -c pytest-cov.ini` - Run tests with coverage configuration
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
Shared utilities that enable type-safe DI across both decorators:
- **`get_all_type_hints()`**: Traverses entire Method Resolution Order (MRO) to collect annotations
- **`needs_implementation()`**: Determines if attributes need synthesis by checking full inheritance hierarchy
- **`is_type_compatible()`**: Validates type compatibility for dependency injection
- **Conservative Approach**: Handles complex types gracefully rather than failing

### Key Architectural Patterns
- **Mediator Pattern**: `@module` acts as central coordinator for all dependencies
- **Factory Pattern**: Generates `@cached_property` or `property` methods for object creation
- **MRO Traversal**: Proper handling of complex inheritance hierarchies
- **Pluggable Caching**: `CachingStrategy` enum applied at decoration time

## Testing Strategy

- **Coverage Achievement**: ~72% test coverage (focused on realistic scenarios)
- **Framework**: pytest with pytest-cov
- **Matrix Testing**: Python 3.8, 3.9, 3.10, 3.11, 3.12, 3.13
- **Test Architecture**: 
  - **Example Tests**: Real-world usage patterns as executable tests in `examples/`
  - **Coverage Separation**: Coverage config in `pytest-cov.ini` for CI/CD, clean config for PyCharm debugging
- **Test Quality**: Prioritize meaningful assertions over empty coverage metrics
- **Realistic Testing**: Remove unrealistic defensive code rather than mock impossible scenarios

### PyCharm Testing Configuration
- **Debugging**: PyCharm uses `pyproject.toml` without coverage for proper breakpoint support
- **Coverage Testing**: Use `./scripts/test-with-coverage.sh` or `pytest -c pytest-cov.ini`
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
- Both decorators use `type_utils.py` for consistent type handling
- `@law_of_demeter` creates properties that `@module` recognizes during validation
- Test decorator cooperation in `test_integration.py` for complex scenarios

### Architectural Decisions
- **Explicit Annotations Required**: Only annotated attributes are forwarded/synthesized
- **Decoration-Time Creation**: Properties exist at class definition time for better IDE support
- **Conservative Type Validation**: Allows complex types rather than failing on edge cases

## Key Features

- Modern Python packaging with pyproject.toml
- Comprehensive testing with coverage enforcement
- Automated CI/CD with GitHub Actions
- Type safety with mypy
- Code quality with ruff and black (configured for Python 3.8+ compatibility)
- Secure PyPI deployment with trusted publishing

## Recent Updates

### Python 3.8 Compatibility
- Added `from __future__ import annotations` to support modern type syntax
- Disabled ruff rules UP006 and UP007 that require Python 3.9+ syntax
- Maintained use of `Type[Any]` and `Union[...]` for broader compatibility

### Testing Infrastructure
- Separated coverage configuration to enable PyCharm debugging
- Added `pytest-cov.ini` for CI/CD coverage requirements  
- Created `scripts/test-with-coverage.sh` for convenient coverage runs
- Added setuptools to dev dependencies for PyCharm's pytest runner