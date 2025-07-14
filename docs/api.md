# API Reference

## Core Decorators

### @module(strategy: CachingStrategy = CachingStrategy.DISABLED)

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

### @law_of_demeter(base_ref: str, prefix: str = "_")

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

## Type Utilities

### is_type_compatible(provided_type: Any, required_type: Any) -> bool

Checks if a provided type is compatible with a required type for dependency injection.

**Logic:**
1. Exact type match: `provided_type == required_type`
2. String annotations: Name-based comparison
3. None types: Must both be None  
4. Class inheritance: `issubclass(provided_type, required_type)`
5. Complex types: Conservative fallback to True

**Note:** Exception handling for `issubclass` TypeError was removed as unrealistic in practice.

### safe_get_type_hints(cls: Type[Any]) -> dict[str, Any]

Safely retrieves type hints with fallback to `__annotations__` on error.

### get_all_type_hints(cls: Type[Any]) -> dict[str, Any]

Collects type hints from entire inheritance hierarchy (MRO).

### needs_implementation(cls: Type[Any], attr_name: str) -> bool

Determines if an attribute needs implementation by checking:
- Has annotation but no implementation
- Is an abstract method/property in inheritance hierarchy

## Enums

### CachingStrategy

Component caching strategies for the `@module` decorator.

- `DISABLED = "disabled"`: No caching, create new instances each time
- `NOT_THREAD_SAFE = "not_thread_safe"`: Cache instances (not thread-safe)