"""Test @law_of_demeter with dataclass base refs.

Dataclass-generated __init__ methods have no inspectable source code,
so has_constructor_assignment must handle OSError from inspect.getsource.

The bug triggers when stacking @law_of_demeter decorators: the outer
decorator probes _-prefixed annotations against its base_ref type. When
an annotation belongs to the *inner* base_ref (not the outer one),
_can_resolve_attribute falls through to has_constructor_assignment, which
crashes on dataclass-generated __init__ with OSError.
"""

from dataclasses import dataclass

from reactor_di import law_of_demeter


@dataclass
class DbConfig:
    host: str = "localhost"
    port: int = 5432


@dataclass
class AppConfig:
    debug: bool = False
    log_level: str = "INFO"


@law_of_demeter("app_config")
@law_of_demeter("db_config")
class Service:
    """Service with stacked @law_of_demeter on two dataclass base refs.

    The outer decorator ("app_config") will probe _host and _port against
    AppConfig — they don't exist there, so it falls through to
    has_constructor_assignment(AppConfig, "host"), which crashes with
    OSError because AppConfig's __init__ is dataclass-generated.
    """

    db_config: DbConfig
    app_config: AppConfig

    # Forwarded from db_config
    _host: str
    _port: int

    # Forwarded from app_config
    _debug: bool
    _log_level: str

    def __init__(self, db_config: DbConfig, app_config: AppConfig) -> None:
        self.db_config = db_config
        self.app_config = app_config


def test_stacked_dataclass_forwarding():
    """Stacked @law_of_demeter on dataclass base refs resolves correctly."""
    svc = Service(DbConfig(), AppConfig())
    assert svc._host == "localhost"
    assert svc._port == 5432
    assert svc._debug is False
    assert svc._log_level == "INFO"


def test_stacked_dataclass_forwarding_custom_values():
    """Stacked @law_of_demeter with custom dataclass values."""
    svc = Service(
        DbConfig(host="db.example.com", port=3306),
        AppConfig(debug=True, log_level="DEBUG"),
    )
    assert svc._host == "db.example.com"
    assert svc._port == 3306
    assert svc._debug is True
    assert svc._log_level == "DEBUG"


def test_single_dataclass_forwarding():
    """Single @law_of_demeter with a dataclass base ref works."""

    @law_of_demeter("config")
    class SimpleService:
        config: DbConfig
        _host: str
        _port: int

        def __init__(self, config: DbConfig) -> None:
            self.config = config

    svc = SimpleService(DbConfig())
    assert svc._host == "localhost"
    assert svc._port == 5432
