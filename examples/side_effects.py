from functools import cached_property

from reactor_di import CachingStrategy, law_of_demeter, module

url_access = 0


class ConnectionConfig:

    @cached_property
    def url(self) -> str:
        global url_access
        url_access += 1
        return "schema://authority/path?query=value#fragment"


@law_of_demeter("_config")
class ConnectionManager:
    _config: ConnectionConfig
    _url: str  # from _config

    def __init__(self):
        self.connections = 0

    def connect(self) -> str:
        self.connections += 1
        return self._url


@law_of_demeter("manager", prefix="")
@module(CachingStrategy.NOT_THREAD_SAFE)
class ConnectionApp:
    config: ConnectionConfig
    manager: ConnectionManager
    connections: int  # from pool

    def connect(self) -> str:
        return self.manager.connect()


def test_side_effects():
    """Test that side effects are properly handled."""

    app = ConnectionApp()

    assert app.connect() == "schema://authority/path?query=value#fragment"
    assert app.connections == 1
    assert url_access == 1

    assert app.connect() == "schema://authority/path?query=value#fragment"
    assert app.connections == 2
    assert url_access == 1
