"""Quick Start example for reactor-di.

This example demonstrates the core functionality of reactor-di:
- Using @law_of_demeter decorator for property forwarding
- Using @module decorator for dependency injection
- Automatic dependency resolution and caching
"""

from reactor_di import CachingStrategy, law_of_demeter, module


class Config:
    """Configuration for database connection."""

    host = "localhost"
    port = 5432
    timeout = 30


class ConfigMixin:
    config: Config


class Database:
    """Database service with configuration forwarding."""

    _host: str  # Forwarded from config.host
    _port: int  # Forwarded from config.port
    _timeout: int  # Forwarded from config.timeout

    def connect(self) -> str:
        """Connect to database and return connection string."""
        return f"Connected to {self._host}:{self._port} (timeout: {self._timeout}s)"


@law_of_demeter("config")
class ConfiguredDatabase(Database, ConfigMixin):
    """Database service with configuration forwarding."""


# Module: Automatic DI: Implements annotations as @cached_property functions
@module(CachingStrategy.NOT_THREAD_SAFE)
class AppModule(ConfigMixin):
    """Application module with dependency injection."""

    database: ConfiguredDatabase  # Synthesized with dependencies


def test_database_connection():
    """Test that database service connects with correct parameters."""
    app = AppModule()
    database = app.database

    # Test the connection string
    connection_result = database.connect()
    assert connection_result == "Connected to localhost:5432 (timeout: 30s)"


def test_property_forwarding():
    """Test that properties are cleanly forwarded from config."""
    app = AppModule()
    database = app.database

    # Test forwarded properties
    assert database._host == "localhost"  # from config.host
    assert database._port == 5432  # from config.port
    assert database._timeout == 30  # from config.timeout


def test_dependency_injection():
    """Test that dependencies are properly injected."""
    app = AppModule()

    # Test that config is available
    assert app.config is not None
    assert isinstance(app.config, Config)

    # Test that database service is available
    assert app.database is not None
    assert isinstance(app.database, Database)

    # Test that the database service has the config injected
    assert app.database.config is app.config


def test_caching_behavior():
    """Test that caching works correctly with NOT_THREAD_SAFE strategy."""
    app = AppModule()

    # Test that multiple calls return the same instance
    database1 = app.database
    database2 = app.database

    assert database1 is database2  # Same instance due to caching

    # Test that config is also cached
    config1 = app.config
    config2 = app.config

    assert config1 is config2  # Same instance due to caching
