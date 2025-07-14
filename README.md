# Reactor DI

[![CI](https://github.com/your-username/reactor-di-python/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/reactor-di-python/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/reactor-di.svg)](https://badge.fury.io/py/reactor-di)
[![Coverage Status](https://codecov.io/gh/your-username/reactor-di-python/branch/main/graph/badge.svg)](https://codecov.io/gh/your-username/reactor-di-python)
[![Python versions](https://img.shields.io/pypi/pyversions/reactor-di.svg)](https://pypi.org/project/reactor-di/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A code generator for dependency injection (DI) in Python based on the mediator and factory patterns.

## Features

- **Two powerful decorators**: `@module` and `@law_of_demeter`
- **Code generation approach**: Generates DI code rather than runtime injection
- **Mediator pattern**: Central coordination of dependencies
- **Factory pattern**: Object creation abstraction
- **Type-safe**: Full type hint support
- **Python 3.8+ support**: Requires Python 3.8+ due to `@cached_property` usage

## Installation

```bash
pip install reactor-di
```

## Quick Start

```python
from reactor_di import module, law_of_demeter

# Usage examples will be added when decorators are implemented
```

## Development

This project uses modern Python tooling and best practices:

- **Package manager**: [uv](https://github.com/astral-sh/uv)
- **Testing**: [pytest](https://pytest.org/) with [coverage](https://coverage.readthedocs.io/)
- **Linting**: [ruff](https://github.com/astral-sh/ruff) and [black](https://black.readthedocs.io/)
- **Type checking**: [mypy](https://mypy.readthedocs.io/)

### Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   uv sync --all-groups
   ```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=reactor_di

# Run specific test file
uv run pytest tests/test_decorators.py
```

### Code Quality

```bash
# Run linting
uv run ruff check src tests
uv run black --check src tests

# Run type checking
uv run mypy src

# Fix formatting
uv run black src tests
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass and coverage is maintained
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.