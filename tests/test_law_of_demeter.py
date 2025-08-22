from .config import Config
from .database import Database


def test_law_of_demeter():
    database = Database(Config())

    # Test the connection string
    connection_result = database.connect()
    assert connection_result == "Connected to localhost:5432 (timeout: 30s)"
