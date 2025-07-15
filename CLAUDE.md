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
- `uv add <package>` - Add a new dependency
- `uv remove <package>` - Remove a dependency

### Testing
- `uv run pytest` - Run all tests with coverage (146 tests including examples)
- `uv run pytest --cov=reactor_di` - Run tests with coverage reporting
- `uv run pytest tests/test_module.py` - Run specific test file
- `uv run pytest examples/` - Run testable examples
- `uv run pytest -m "not slow"` - Skip slow tests

### Code Quality
- `uv run ruff check src tests examples` - Run linting
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
├── tests/                      # Test suite (100% coverage)
│   ├── test_module.py          # Tests for @module decorator
│   ├── test_law_of_demeter.py  # Tests for @law_of_demeter decorator  
│   ├── test_type_utils.py      # Tests for type compatibility utilities
│   └── test_integration.py     # Integration tests between decorators
├── examples/                   # Testable examples (19 additional tests)
│   ├── __init__.py             # Package initialization
│   ├── quick_start.py          # Quick Start example as tests
│   ├── caching_strategies.py   # Caching strategy examples
│   ├── multiple_decorators.py  # Multiple decorator examples
│   └── custom_prefixes.py      # Custom prefix examples
├── docs/                       # Documentation
├── .github/workflows/          # CI/CD pipelines
│   ├── ci.yml                 # Matrix testing across Python versions
│   └── publish.yml            # PyPI deployment
└── pyproject.toml             # Modern Python configuration
```

## Architecture

This is a **code generator** for dependency injection, not a runtime DI framework. The architecture is based on:

- **Mediator Pattern**: Central coordination of dependencies
- **Factory Pattern**: Object creation abstraction
- **Code Generation**: Produces DI code rather than runtime injection
- **Two Decorators**: `@module` and `@law_of_demeter`
- **Python 3.8+ Required**: Uses `@cached_property` decorator

## Testing Strategy

- **Coverage Achievement**: 100% test coverage maintained across all modules
- **Framework**: pytest with pytest-cov
- **Matrix Testing**: Python 3.8, 3.9, 3.10, 3.11, 3.12, 3.13
- **Coverage Reports**: HTML, XML, and terminal output  
- **Test Quality**: Prioritize meaningful assertions over empty coverage metrics
- **Realistic Testing**: Remove unrealistic defensive code rather than mock impossible scenarios
- **Test Architecture**: Modular test files with dedicated coverage for each component

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

## Key Features

- Modern Python packaging with pyproject.toml
- Comprehensive testing with coverage enforcement
- Automated CI/CD with GitHub Actions
- Type safety with mypy
- Code quality with ruff and black
- Secure PyPI deployment with trusted publishing