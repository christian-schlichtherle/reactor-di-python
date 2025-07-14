# Reactor DI Documentation

Welcome to the Reactor DI documentation. This is a code generator for dependency injection (DI) in Python based on the mediator and factory patterns.

## Overview

Reactor DI provides two powerful decorators for clean dependency injection:
- `@module` - Automatic dependency injection containers with caching strategies
- `@law_of_demeter` - Property forwarding to avoid Law of Demeter violations

The library emphasizes **code generation** over runtime injection, creating clean, type-safe dependency management.

## Installation

```bash
pip install reactor-di
```

## Quick Start

```python
from abc import ABC
from reactor_di import module, law_of_demeter, CachingStrategy

# Configuration class
class Config:
    host = "localhost"
    port = 5432

# Service with dependency injection
class DatabaseService(ABC):
    _config: Config
    _host: str    # Forwarded from config.host
    _port: int    # Forwarded from config.port

# Create clean property forwarding
@law_of_demeter("_config")
class CleanDatabaseService(DatabaseService):
    pass

# Dependency injection module
@module(CachingStrategy.NOT_THREAD_SAFE)
class AppModule:
    config: Config
    database: CleanDatabaseService

# Usage
app = AppModule()
db = app.database
print(f"Connecting to {db._host}:{db._port}")
```

## Key Features

- **100% Test Coverage**: Comprehensive test suite with meaningful assertions
- **Type Safety**: Full type hint support with realistic type compatibility checking
- **Modular Architecture**: Clean separation between decorators and utilities
- **Python 3.8+ Support**: Modern Python features with backward compatibility

## API Reference

See the [API documentation](api.md) for detailed information about all decorators and utilities.