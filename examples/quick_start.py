"""Quick Start example for reactor-di.

This example demonstrates the core functionality of reactor-di:
- Using @law_of_demeter decorator for property forwarding
- Using @module decorator for dependency injection
- Automatic dependency resolution and caching
"""

from reactor_di import module, law_of_demeter, CachingStrategy


class DatabaseConfig:
    """Configuration for database connection."""
    host = "localhost"
    port = 5432
    timeout = 30


@law_of_demeter("_config")
class DatabaseService:
    """Database service with configuration forwarding."""
    _config: DatabaseConfig
    _host: str      # Forwarded from config.host
    _port: int      # Forwarded from config.port
    _timeout: int   # Forwarded from config.timeout
    
    def connect(self) -> str:
        """Connect to database and return connection string."""
        return f"Connected to {self._host}:{self._port} (timeout: {self._timeout}s)"


# Module: Automatic DI: Implements annotations as @cached_property functions
@module(CachingStrategy.NOT_THREAD_SAFE)
class AppModule:
    """Application module with dependency injection."""
    config: DatabaseConfig      # Directly instantiated
    database: DatabaseService   # Synthesized with dependencies


def test_database_connection():
    """Test that database service connects with correct parameters."""
    app = AppModule()
    db_service = app.database
    
    # Test the connection string
    connection_result = db_service.connect()
    assert connection_result == "Connected to localhost:5432 (timeout: 30s)"


def test_property_forwarding():
    """Test that properties are cleanly forwarded from config."""
    app = AppModule()
    db_service = app.database
    
    # Test forwarded properties
    assert db_service._host == "localhost"      # from config.host
    assert db_service._port == 5432            # from config.port
    assert db_service._timeout == 30           # from config.timeout


def test_dependency_injection():
    """Test that dependencies are properly injected."""
    app = AppModule()
    
    # Test that config is available
    assert app.config is not None
    assert isinstance(app.config, DatabaseConfig)
    
    # Test that database service is available
    assert app.database is not None
    assert isinstance(app.database, DatabaseService)
    
    # Test that the database service has the config injected
    assert app.database._config is app.config


def test_caching_behavior():
    """Test that caching works correctly with NOT_THREAD_SAFE strategy."""
    app = AppModule()
    
    # Test that multiple calls return the same instance
    db_service1 = app.database
    db_service2 = app.database
    
    assert db_service1 is db_service2  # Same instance due to caching
    
    # Test that config is also cached
    config1 = app.config
    config2 = app.config
    
    assert config1 is config2  # Same instance due to caching

