"""Example: Testing @module classes by replacing components with mocks.

Demonstrates the recommended pattern for testing modules:

1. Instantiate the module
2. Replace selected components with mocks **before first access**
3. Access the component under test — it receives the mocks via DI

This works because ``NOT_THREAD_SAFE`` and ``THREAD_SAFE`` use non-data
descriptors (``cached_property`` / ``thread_safe_cached_property``).
Setting an attribute on the instance puts the value into ``__dict__``,
which takes priority over non-data descriptors on subsequent access.

Dependencies are resolved lazily: a component's ``__getattr__`` calls
``getattr(module_ref, dep_name)`` on first access, so it picks up
whatever is on the module at that point — real factory or mock.
"""

from typing import cast

from reactor_di import CachingStrategy, law_of_demeter, lookup, module

# ---------------------------------------------------------------------------
# Production code: a realistic multi-component module
# ---------------------------------------------------------------------------


class Config:
    host = "db.prod.internal"
    port = 5432
    timeout = 30
    api_url = "https://api.prod.internal"


class Database:
    def __init__(self) -> None:
        self.connected = True

    def query(self, sql: str) -> str:
        return f"prod-result: {sql}"


@law_of_demeter("_config")
class ApiClient:
    _config: Config
    _api_url: str
    _timeout: int

    def __init__(self) -> None:
        pass

    def get(self, path: str) -> str:
        return f"GET {self._api_url}{path} (timeout={self._timeout})"


@law_of_demeter("_db")
class UserRepository:
    _db: Database

    def __init__(self) -> None:
        pass

    def find(self, user_id: int) -> str:
        return self._db.query(f"SELECT * FROM users WHERE id={user_id}")


@law_of_demeter("_api")
class NotificationService:
    _api: ApiClient

    def __init__(self) -> None:
        pass

    def notify(self, user_id: int, message: str) -> str:
        return self._api.get(f"/notify?user={user_id}&msg={message}")


@module(CachingStrategy.NOT_THREAD_SAFE)
class AppModule:
    config: Config
    db: Database
    api: ApiClient
    user_repo: UserRepository
    notifications: NotificationService


# ---------------------------------------------------------------------------
# Tests: replace components with mocks before first access
# ---------------------------------------------------------------------------


def test_replace_single_component():
    """Replace one component with a mock; others use real factories."""
    app = AppModule()

    # Mock only the database
    mock_db = Database()
    mock_db.query = lambda sql: f"mock-result: {sql}"  # type: ignore[method-assign]
    app.db = mock_db

    # user_repo picks up the mock database via DI
    result = app.user_repo.find(42)
    assert "mock-result:" in result
    assert "id=42" in result

    # api client still uses the real config factory
    assert app.api._api_url == "https://api.prod.internal"


def test_replace_multiple_components():
    """Replace several components to isolate the component under test."""
    app = AppModule()

    # Mock config and database
    mock_config = Config()
    mock_config.api_url = "https://api.test.local"
    mock_config.timeout = 1
    app.config = mock_config

    mock_db = Database()
    mock_db.query = lambda sql: f"test-db: {sql}"  # type: ignore[method-assign]
    app.db = mock_db

    # api client gets mock config
    assert app.api.get("/health") == "GET https://api.test.local/health (timeout=1)"

    # user_repo gets mock database
    assert "test-db:" in app.user_repo.find(1)


def test_partial_mock_real_config():
    """Only mock the database; config and API client use real factories."""
    app = AppModule()

    mock_db = Database()
    mock_db.connected = False
    mock_db.query = lambda sql: "connection-refused"  # type: ignore[method-assign]
    app.db = mock_db

    # Real config flows through to real API client
    assert app.config.host == "db.prod.internal"
    assert app.api._timeout == 30

    # But user_repo gets the mock database
    assert app.user_repo.find(1) == "connection-refused"


def test_mock_is_identity_stable():
    """The mock instance is the exact object injected — no copying."""
    app = AppModule()

    mock_db = Database()
    app.db = mock_db

    # The module returns the exact mock
    assert app.db is mock_db
    # The component receives the exact mock
    assert app.user_repo._db is mock_db


def test_cached_component_picks_up_later_mock():
    """Access a component first, then mock its dependency.

    Because dependency resolution is lazy (per-attribute via __getattr__),
    a cached component whose dependency hasn't been accessed yet will
    still pick up a mock set on the module afterward.
    """
    app = AppModule()

    # Access user_repo — the component is created and cached
    user_repo = app.user_repo

    # Now mock the database AFTER the component was created
    mock_db = Database()
    mock_db.query = lambda sql: f"late-mock: {sql}"  # type: ignore[method-assign]
    app.db = mock_db

    # user_repo._db hasn't been accessed yet, so __getattr__ resolves it now
    # and picks up the mock we just set
    assert "late-mock:" in user_repo.find(7)


# ---------------------------------------------------------------------------
# THREAD_SAFE: same pattern works
# ---------------------------------------------------------------------------


@module(CachingStrategy.THREAD_SAFE)
class ThreadSafeModule:
    config: Config
    db: Database
    user_repo: UserRepository


def test_thread_safe_module_mock():
    """Mock replacement works identically with THREAD_SAFE caching."""
    app = ThreadSafeModule()

    mock_db = Database()
    mock_db.query = lambda sql: f"ts-mock: {sql}"  # type: ignore[method-assign]
    app.db = mock_db

    assert "ts-mock:" in app.user_repo.find(99)
    assert app.user_repo._db is mock_db


# ---------------------------------------------------------------------------
# Nested modules with lookup: mock at the root, children see it
# ---------------------------------------------------------------------------


@module(CachingStrategy.NOT_THREAD_SAFE)
class ChildModule:
    db: lookup[Database]
    user_repo: UserRepository


@module(CachingStrategy.NOT_THREAD_SAFE)
class ParentModule:
    config: Config
    db: Database
    child: ChildModule


def test_nested_module_mock():
    """Mock a root dependency; child modules receive it through lookup."""
    app = ParentModule()

    mock_db = Database()
    mock_db.query = lambda sql: f"nested-mock: {sql}"  # type: ignore[method-assign]
    app.db = mock_db

    # child module's lookup[Database] resolves from parent.
    # cast() narrows lookup[Database] to Database at the access site —
    # the marker resolves to its inner type at runtime.
    assert cast("Database", app.child.db) is mock_db
    # component inside child module gets the mock too
    assert "nested-mock:" in app.child.user_repo.find(3)
