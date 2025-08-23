# Reactor DI for Python

[![CI](https://github.com/christian-schlichtherle/reactor-di-python/actions/workflows/ci.yaml/badge.svg)](https://github.com/christian-schlichtherle/reactor-di-python/actions/workflows/ci.yaml)
[![Coverage Status](https://codecov.io/gh/christian-schlichtherle/reactor-di-python/branch/main/graph/badge.svg)](https://codecov.io/gh/christian-schlichtherle/reactor-di-python)
[![PyPI version](https://img.shields.io/pypi/v/reactor-di.svg)](https://pypi.org/project/reactor-di/)
[![Python versions](https://img.shields.io/pypi/pyversions/reactor-di.svg)](https://pypi.org/project/reactor-di/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A code generator for dependency injection (DI) in Python which is based on the mediator and factory patterns.

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
from reactor_di import module, law_of_demeter, CachingStrategy

class DatabaseConfig:
    host = "localhost"
    port = 5432
    timeout = 30

@law_of_demeter("_config")
class DatabaseService:
    _config: DatabaseConfig
    _host: str      # Forwarded from config.host
    _port: int      # Forwarded from config.port
    _timeout: int   # Forwarded from config.timeout
    
    def connect(self) -> str:
        return f"Connected to {self._host}:{self._port} (timeout: {self._timeout}s)"

# Module: Automatic DI: Implements annotations as @cached_property functions
@module(CachingStrategy.NOT_THREAD_SAFE)
class AppModule:
    config: DatabaseConfig      # Directly instantiated
    database: DatabaseService   # Synthesized with dependencies

# Usage
app = AppModule()
db_service = app.database
print(db_service.connect())  # → "Connected to localhost:5432 (timeout: 30s)"

# Properties are cleanly forwarded
print(db_service._host)      # → "localhost" (from config.host)
print(db_service._timeout)   # → 30 (from config.timeout)
```

## Examples

The `examples/` directory contains testable examples that demonstrate all the features shown in this README:

- **`quick_start.py`** - The complete Quick Start example above, converted to testable format
- **`quick_start_advanced.py`** - Advanced quick start with inheritance patterns
- **`caching_strategy.py`** - Demonstrates `CachingStrategy.DISABLED` vs `CachingStrategy.NOT_THREAD_SAFE`
- **`stacked_decorators.py`** - Shows using multiple `@law_of_demeter` decorators on the same class
- **`custom_prefix.py`** - Demonstrates custom prefix options (`prefix=''`, `prefix='cfg_'`, etc.)
- **`side_effects.py`** - Tests side effect isolation during decoration

### Running Examples

```bash
# Run all examples as tests
uv run pytest examples/

# Run a specific example
uv run pytest examples/quick_start.py
```

All examples are automatically tested as part of the CI pipeline to ensure they stay current with the codebase.

## Architecture

Reactor DI uses a **code generation approach** with clean separation of concerns:

- **`module.py`** - The `@module` decorator for dependency injection containers
- **`law_of_demeter.py`** - The `@law_of_demeter` decorator for property forwarding
- **`caching.py`** - Caching strategies (`CachingStrategy.DISABLED`, `CachingStrategy.NOT_THREAD_SAFE`)
- **`type_utils.py`** - Simplified type checking utilities (Python 3.8+ stable APIs)

The decorators work together through simple `hasattr` checks - `@law_of_demeter` creates forwarding properties that `@module` recognizes as already implemented, enabling clean cooperation without complex validation logic.

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

## API Reference

### Core Decorators

#### @module(strategy: CachingStrategy = CachingStrategy.DISABLED)

Creates a dependency injection module that automatically instantiates and provides dependencies.

**Parameters:**
- `strategy`: Caching strategy for component instances
  - `CachingStrategy.DISABLED`: Create new instances each time (default)
  - `CachingStrategy.NOT_THREAD_SAFE`: Cache instances (not thread-safe)

**Usage:**
```python
@module(CachingStrategy.NOT_THREAD_SAFE)
class AppModule:
    config: Config
    service: Service  # Automatically injected with dependencies
```

#### @law_of_demeter(base_ref: str, prefix: str = "_")

Creates property forwarding from a base reference to avoid Law of Demeter violations.

**Parameters:**
- `base_ref`: Name of the base object attribute to forward from
- `prefix`: Prefix for forwarded property names (default: "_")

**Usage:**
```python
@law_of_demeter("_config")
class Service:
    _timeout: int     # Forwards to _config.timeout
    _host: str        # Forwards to _config.host
```

### Type Utilities

The simplified type utilities leverage Python 3.8+ stable type hint APIs:

#### get_alternative_names(name: str, prefix: str = "_") -> List[str]

Generates alternative names for dependency mapping (e.g., `_config` → `config`).

#### has_constructor_assignment(class_type: Type[Any], attr_name: str) -> bool

Detects if a constructor assigns to an attribute using regex source analysis.

#### is_primitive_type(attr_type: Type[Any]) -> bool

Identifies primitive types (int, str, bool, etc.) that shouldn't be auto-instantiated.

### Enums

#### CachingStrategy

Component caching strategies for the `@module` decorator.

- `DISABLED = "disabled"`: No caching, create new instances each time
- `NOT_THREAD_SAFE = "not_thread_safe"`: Cache instances (not thread-safe)

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
   uv sync
   ```

### Running Tests

```bash
# Run tests without coverage (default, fast for development)
uv run pytest

# Run tests with coverage and HTML/terminal reports
uv run pytest --cov

# Run example tests
uv run pytest examples/                     # Run all examples as tests (20 tests)
uv run pytest examples/caching_strategy.py  # Caching strategy examples (3 tests)
uv run pytest examples/custom_prefix.py     # Custom prefix examples (6 tests)
uv run pytest examples/quick_start.py       # Quick start examples (4 tests)
```

### Debugging in PyCharm

The project is optimized for fast development and debugging:

1. **Default**: Tests run without coverage for fast feedback and debugging
2. **Coverage analysis**: Use `--cov` flag when you need coverage reports
3. **Coverage threshold**: Set to 90% to maintain high code quality (when coverage is enabled)

This configuration ensures breakpoints work reliably and tests run quickly during development.

### Code Quality

```bash
# Run linting
uv run ruff check src tests examples
uv run black --check src tests examples

# Run type checking
uv run mypy src

# Fix formatting
uv run black src tests examples
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality with meaningful assertions
5. Ensure all tests pass and 90% coverage is maintained  
6. Verify realistic code scenarios rather than mocking impossible edge cases
7. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.