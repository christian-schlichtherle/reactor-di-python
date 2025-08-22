class Config:
    """Configuration for database connection."""

    timeout: int = 30

    def __init__(self) -> None:
        self.host = "localhost"
        self.port = 5432
