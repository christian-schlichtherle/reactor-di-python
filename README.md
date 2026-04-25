# Reactor DI for Python

[![CI](https://github.com/christian-schlichtherle/reactor-di-python/actions/workflows/ci.yaml/badge.svg)](https://github.com/christian-schlichtherle/reactor-di-python/actions/workflows/ci.yaml)
[![Coverage Status](https://codecov.io/gh/christian-schlichtherle/reactor-di-python/branch/main/graph/badge.svg)](https://codecov.io/gh/christian-schlichtherle/reactor-di-python)
[![PyPI version](https://img.shields.io/pypi/v/reactor-di.svg)](https://pypi.org/project/reactor-di/)
[![Python versions](https://img.shields.io/pypi/pyversions/reactor-di.svg)](https://pypi.org/project/reactor-di/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A code generator for dependency injection (DI) in Python which is based on the mediator and factory patterns.

## Features

- **Two powerful decorators**: `@module` and `@law_of_demeter`, plus `lookup` and `make` annotation markers
- **Code generation approach**: Generates DI code rather than runtime injection
- **Mediator pattern**: Central coordination of dependencies
- **Factory pattern**: Object creation abstraction
- **Type-safe**: Full type hint support
- **Nested modules**: Child modules use `lookup[Type]` to share dependencies from parent modules
- **Lazy dependency resolution**: Dependencies resolved individually on first access, supporting deferred initialization patterns (e.g., async context managers)
- **TYPE_CHECKING compatible**: Works with `if TYPE_CHECKING:` imports for circular dependency avoidance
- **Pydantic compatible**: Works with Pydantic BaseSettings/BaseModel annotation-only fields
- **ABC compatible**: Automatic resolution of abstract `@property` conflicts with DI annotations
- **Python 3.9+ support**: Tested on Python 3.9 through 3.14

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
- **`caching_strategy.py`** - Demonstrates `CachingStrategy.DISABLED`, `CachingStrategy.NOT_THREAD_SAFE`, and `CachingStrategy.THREAD_SAFE`
- **`make_marker.py`** - Subtype factory generation with `make[BaseType, ImplType]`
- **`nested_modules.py`** - Nested modules with `lookup` for parent dependency sharing
- **`stacked_decorators.py`** - Shows using multiple `@law_of_demeter` decorators on the same class
- **`custom_prefix.py`** - Demonstrates custom prefix options (`prefix=''`, `prefix='cfg_'`, etc.)
- **`side_effects.py`** - Tests side effect isolation during decoration
- **`testing.py`** - Testing pattern: replacing module components with mocks
- **`typing_decorators_preserve_class_type.py`** - Demonstrates (and statically asserts via `mypy`) that `@law_of_demeter` and `@module` preserve the input class type
- **`typing_lookup_make_erasure.py`** - Demonstrates (and statically asserts via `mypy`) that `lookup[T]` and `make[B, I]` erase to `T` / `B` for type checkers, so attribute access type-checks without `cast()`

### Running Examples

```bash
# Run all examples as tests
uv run pytest examples/

# Run a specific example
uv run pytest examples/quick_start.py
```

All examples are automatically tested as part of the CI pipeline to ensure they stay current with the codebase.

## Tests

The `tests/` directory contains regression and unit tests (49 tests):

- **`test_module_integration.py`** - Module + law_of_demeter integration with annotation-only configs, Pydantic compatibility, and abstract property conflict resolution
- **`test_lazy_resolution.py`** - Lazy per-attribute resolution with deferred initialization patterns
- **`test_forward_ref.py`** - TYPE_CHECKING forward reference handling in module factory
- **`test_dataclass_law_of_demeter.py`** - Dataclass + stacked @law_of_demeter regression tests (3 tests)
- **`test_pure_hasattr.py`** - Comprehensive tests for the `pure_hasattr` utility (14 tests)
- **`test_thread_safe.py`** - Thread-safe caching strategy with concurrent access tests (12 tests)
- **`test_law_of_demeter.py`** - Law of Demeter decorator tests
- **`test_side_effects.py`** - Side effects isolation during decoration

```bash
# Run all tests (examples + regression tests)
uv run pytest

# Run only regression tests
uv run pytest tests/
```

## Architecture

Reactor DI uses a **code generation approach** with clean separation of concerns:

- **`module.py`** - The `@module` decorator for dependency injection containers
- **`law_of_demeter.py`** - The `@law_of_demeter` decorator for property forwarding
- **`caching.py`** - Caching strategies (`CachingStrategy.DISABLED`, `CachingStrategy.NOT_THREAD_SAFE`, `CachingStrategy.THREAD_SAFE`)
- **`type_utils.py`** - Simplified type checking utilities and the `lookup`/`make` annotation markers (Python 3.9+ stable APIs)

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

# Cached components - same instance returned (thread-safe, uses locking)
@module(CachingStrategy.THREAD_SAFE)
class ThreadSafeProdModule:
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

### Subtype Factory Generation

Use `make[BaseType, ImplType]` to program to an interface while the factory instantiates a concrete implementation:

```python
from abc import ABC, abstractmethod
from reactor_di import module, make, CachingStrategy

class Logger(ABC):
    @abstractmethod
    def log(self, message: str) -> str: ...

class ConsoleLogger(Logger):
    def log(self, message: str) -> str:
        return f"[console] {message}"

@module(CachingStrategy.NOT_THREAD_SAFE)
class AppModule:
    logger: make[Logger, ConsoleLogger]   # factory returns ConsoleLogger()

app = AppModule()
assert isinstance(app.logger, ConsoleLogger)
assert isinstance(app.logger, Logger)
```

### Nested Modules

Child modules can share dependencies from their parent using `lookup[Type]`:

```python
from reactor_di import module, lookup, CachingStrategy

@module(CachingStrategy.NOT_THREAD_SAFE)
class CacheModule:
    db: lookup[DatabaseConnection]   # resolved from parent module
    cache_config: CacheConfig        # created locally

@module(CachingStrategy.NOT_THREAD_SAFE)
class AppModule:
    db: DatabaseConnection           # created here
    cache_module: CacheModule        # child module — db injected from here

app = AppModule()
assert app.cache_module.db is app.db  # same instance
```

An optional second parameter renames the lookup — the child uses a different local name than the parent's attribute:

```python
@module(CachingStrategy.NOT_THREAD_SAFE)
class AuditModule:
    connection: lookup[DatabaseConnection, "db"]  # look up "db" on parent, bind as "connection"
```

On a component (non-module class), `@law_of_demeter` skips `lookup`-annotated attributes — the parent module's factory resolves them through the dependency-map mechanism instead of forwarding from the base reference.

`lookup[T]` and `make[B, I]` erase to `T` / `B` at type-check time (mirroring how `Final[T]` and `ClassVar[T]` erase to `T`), so attribute access works naturally in IDEs and `mypy` without `cast()`.

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
  - `CachingStrategy.THREAD_SAFE`: Cache instances with per-instance locking (thread-safe)

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

### Annotation Markers

#### lookup[Type]

Marks a module annotation as a dependency that should be resolved from the parent module rather than being created locally. On a module, `@module` skips factory generation and installs a lightweight property; the actual value is injected lazily by the parent. On a component, `lookup` is a no-op.

**Parameters:**
- First (required): The type of the dependency
- Second (optional): Name of the attribute to look up on the parent module. Defaults to the annotation's own name.

**Usage:**
```python
@module(CachingStrategy.NOT_THREAD_SAFE)
class ChildModule:
    shared_db: lookup[DatabaseConnection]              # lookup "shared_db" on parent
    connection: lookup[DatabaseConnection, "db"]        # lookup "db" on parent, bind as "connection"
    local_service: MyService                           # created locally
```

#### make[BaseType, ImplType]

Marks a module annotation for subtype factory generation. The factory instantiates `ImplType` (a subtype of `BaseType`) instead of `BaseType`. This enables programming to interfaces while keeping concrete wiring in one place.

**Parameters:**
- First (required): The base type (used for the property return type)
- Second (required): The implementation type (actually instantiated by the factory)

**Usage:**
```python
@module(CachingStrategy.NOT_THREAD_SAFE)
class AppModule:
    service: make[ServiceBase, HttpService]   # factory returns HttpService()
    cache: make[Cache, InMemoryCache]         # factory returns InMemoryCache()
```

### Type Utilities

The simplified type utilities leverage Python 3.9+ stable type hint APIs:

#### get_alternative_names(name: str, prefix: str = "_") -> list[str]

Generates alternative names for dependency mapping (e.g., `_config` → `config`).

#### has_constructor_assignment(class_type: type[Any], attr_name: str) -> bool

Detects if a constructor assigns to an attribute using regex source analysis.

#### is_primitive_type(attr_type: type[Any]) -> bool

Identifies primitive types (int, str, bool, etc.) that shouldn't be auto-instantiated.

#### resolve_abstract_property_conflicts(cls: type[Any]) -> None

Replaces inherited abstract `@property` methods that collide with DI annotations, installing concrete dict-backed properties so lazy DI resolution via `__getattr__` works correctly. Safe to call multiple times.

#### pure_hasattr(obj: Any, attr_name: str) -> bool

Checks if an attribute exists without side effects like triggering descriptors or properties. Used internally to avoid premature evaluation during dependency resolution.

### Enums

#### CachingStrategy

Component caching strategies for the `@module` decorator.

- `DISABLED = "disabled"`: No caching, create new instances each time
- `NOT_THREAD_SAFE = "not_thread_safe"`: Cache instances (not thread-safe)
- `THREAD_SAFE = "thread_safe"`: Cache instances with per-instance locking (thread-safe)

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
# Run all tests (102 tests: 53 examples + 49 regression/unit tests)
uv run pytest

# Run tests with coverage and HTML/terminal reports
uv run pytest --cov

# Run example tests only
uv run pytest examples/                     # Run all examples as tests (53 tests)
uv run pytest examples/caching_strategy.py  # Caching strategy examples (5 tests)
uv run pytest examples/custom_prefix.py     # Custom prefix examples (6 tests)
uv run pytest examples/quick_start.py       # Quick start examples (4 tests)

# Run regression/unit tests only
uv run pytest tests/                        # Run all regression tests (49 tests)
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
uv run mypy src examples

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