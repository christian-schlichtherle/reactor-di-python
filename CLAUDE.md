# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A code generator for dependency injection (DI) in Python based on the mediator and factory patterns. This is a modern, production-ready Python package with comprehensive tooling.

## Development Environment

- **Python Version**: 3.9 for development (requires 3.8+ due to `@cached_property`)
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
- Code quality with ruff (linting) and black (formatting) - configured for Python 3.8+ compatibility
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