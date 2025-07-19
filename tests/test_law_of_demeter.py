from reactor_di import law_of_demeter


class Config:
    """Configuration for database connection."""

    def __init__(self) -> None:
        self.host = "localhost"
        self.port = 5432
        self.timeout = 30


@law_of_demeter("_config")
class Database:
    """Database service with configuration forwarding."""

    _config: Config  # just trying to confuse the decorator
    _host: str  # Forwarded from config.host
    _implemented: str = "implemented"
    _not_implemented: str
    _port: int  # Forwarded from config.port
    _timeout: int  # Forwarded from config.timeout
    also_not_implemented: str

    def __init__(self, config: Config) -> None:
        self._config = config

    def connect(self) -> str:
        """Connect to database and return connection string."""
        return f"Connected to {self._host}:{self._port} (timeout: {self._timeout}s)"


def test_not_needs_implementation():
    database = Database(Config())

    # Test the connection string
    connection_result = database.connect()
    assert connection_result == "Connected to localhost:5432 (timeout: 30s)"
