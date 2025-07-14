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
from abc import ABC
from reactor_di import module, law_of_demeter, CachingStrategy

# Example: Database service with configuration forwarding
class DatabaseConfig:
    host = "localhost"
    port = 5432
    timeout = 30

class DatabaseService(ABC):
    _config: DatabaseConfig
    _host: str      # Forwarded from config.host
    _port: int      # Forwarded from config.port
    _timeout: int   # Forwarded from config.timeout
    
    def connect(self) -> str:
        return f"Connected to {self._host}:{self._port} (timeout: {self._timeout}s)"

# Law of Demeter: Create forwarding properties for clean access
@law_of_demeter("_config")
class CleanDatabaseService(DatabaseService):
    pass

# Module: Automatic dependency injection with caching
@module(CachingStrategy.NOT_THREAD_SAFE)
class AppModule:
    config: DatabaseConfig      # Directly instantiated
    database: CleanDatabaseService  # Synthesized with dependencies

# Usage
app = AppModule()
db_service = app.database
print(db_service.connect())  # → "Connected to localhost:5432 (timeout: 30s)"

# Properties are cleanly forwarded
print(db_service._host)      # → "localhost" (from config.host)
print(db_service._timeout)   # → 30 (from config.timeout)
```

## Architecture

Reactor DI uses a **modular file structure** for clean separation of concerns:

- **`module.py`** - The `@module` decorator for dependency injection containers
- **`law_of_demeter.py`** - The `@law_of_demeter` decorator for property forwarding
- **`caching.py`** - Caching strategies (`CachingStrategy.DISABLED`, `CachingStrategy.NOT_THREAD_SAFE`)
- **`type_utils.py`** - Shared type checking utilities used across decorators

The decorators work together seamlessly - `@law_of_demeter` creates forwarding properties that `@module` recognizes during dependency validation, enabling clean cooperation without special configuration.

## Advanced Usage

### Caching Strategies

```python
from reactor_di import module, CachingStrategy

# No caching - components created fresh each time
@module(CachingStrategy.DISABLED)
class DevModule:
    service: MyService

# Cached components - same instance returned (not thread-safe)
@module(CachingStrategy.NOT_THREAD_SAFE)
class ProdModule:
    service: MyService
```

### Multiple Decorator Integration

```python
@law_of_demeter("_config")    # Creates forwarding properties
@law_of_demeter("_module")    # Auto-setup: self._config = self._module.config
class ResourceController:
    def __init__(self, module):
        self._module = module
        # Decorator automatically sets up: self._config = module.config
    
    # From _config
    _timeout: int
    _is_dry_run: bool
    
    # From _module  
    _api: object
    _namespace: str
```

### Custom Prefixes

```python
# No prefix - direct forwarding
@law_of_demeter('config', prefix='')
class DirectController:
    timeout: int        # → config.timeout
    is_dry_run: bool    # → config.is_dry_run

# Custom prefix
@law_of_demeter('config', prefix='cfg_')
class PrefixController:
    cfg_timeout: int        # → config.timeout
    cfg_is_dry_run: bool    # → config.is_dry_run
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
# Run all tests (126 tests, 100% coverage)
uv run pytest

# Run tests with coverage reporting
uv run pytest --cov=reactor_di

# Run specific test modules
uv run pytest tests/test_module.py          # Module decorator tests
uv run pytest tests/test_law_of_demeter.py  # Law of Demeter decorator tests  
uv run pytest tests/test_type_utils.py      # Type compatibility utilities tests
uv run pytest tests/test_integration.py     # Integration tests between decorators
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
4. Add tests for new functionality with meaningful assertions
5. Ensure all tests pass and 100% coverage is maintained  
6. Verify realistic code scenarios rather than mocking impossible edge cases
7. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.