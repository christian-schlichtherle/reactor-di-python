from reactor_di import law_of_demeter

from .config import Config


@law_of_demeter("_config")
class Database:
    """Database service with configuration forwarding."""

    _config: Config
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
