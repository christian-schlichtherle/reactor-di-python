"""Example: Nested modules with lookup for parent dependency resolution.

Demonstrates how child modules can declare dependencies that should be
resolved from their parent module rather than being created locally.

When a module annotation is wrapped with ``lookup[X]``, the ``@module``
decorator does NOT generate a factory for it.  Instead, a lightweight
dict-backed property is installed so the name is visible to child
component factories.  The actual value is injected lazily by the parent
module through the existing dependency-map mechanism.

An optional second parameter renames the lookup::

    conn: lookup[DatabaseConnection, "db"]   # look up "db" on parent, bind as "conn"
"""

from reactor_di import CachingStrategy, law_of_demeter, lookup, module

# ---------------------------------------------------------------------------
# Shared infrastructure
# ---------------------------------------------------------------------------


class DatabaseConfig:
    host = "db.example.com"
    port = 5432


class DatabaseConnection:
    """Expensive resource that should be shared across child modules."""

    def __init__(self) -> None:
        self.connected = True

    def query(self, sql: str) -> str:
        return f"result of: {sql}"


# ---------------------------------------------------------------------------
# Components used inside child modules
# ---------------------------------------------------------------------------


@law_of_demeter("_db")
class UserRepository:
    """Repository that depends on a DatabaseConnection.

    When created inside a child module, ``_db`` is resolved from the child
    module which in turn got it from the parent via ``lookup``.
    """

    _db: DatabaseConnection

    def __init__(self) -> None:
        pass

    def find_user(self, user_id: int) -> str:
        return self._db.query(f"SELECT * FROM users WHERE id = {user_id}")


@law_of_demeter("_db")
class OrderRepository:
    _db: DatabaseConnection

    def __init__(self) -> None:
        pass

    def find_order(self, order_id: int) -> str:
        return self._db.query(f"SELECT * FROM orders WHERE id = {order_id}")


# ---------------------------------------------------------------------------
# Child modules — use lookup[] to share parent dependencies
# ---------------------------------------------------------------------------


@module(CachingStrategy.NOT_THREAD_SAFE)
class UserModule:
    """Child module that shares the parent's database connection.

    ``db`` is marked with ``lookup`` — @module will NOT generate a factory
    for it.  Instead, when the parent module creates this child, it injects
    its own ``db`` instance through the standard dependency-map mechanism.
    """

    db: lookup[DatabaseConnection]  # resolved from parent module
    user_repo: UserRepository  # created locally, gets db via DI


@module(CachingStrategy.NOT_THREAD_SAFE)
class OrderModule:
    """Another child module sharing the same parent database connection."""

    db: lookup[DatabaseConnection]  # resolved from parent module
    order_repo: OrderRepository  # created locally, gets db via DI


# ---------------------------------------------------------------------------
# Parent module — owns the shared dependency
# ---------------------------------------------------------------------------


@module(CachingStrategy.NOT_THREAD_SAFE)
class AppModule:
    """Top-level module that provides shared dependencies to child modules."""

    db_config: DatabaseConfig
    db: DatabaseConnection  # created once here
    user_module: UserModule  # child module — db injected from here
    order_module: OrderModule  # another child — same db injected


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_child_module_receives_parent_dependency():
    """The child module's lookup dependency is the same instance as the parent's."""
    app = AppModule()

    assert app.user_module.db is app.db
    assert app.order_module.db is app.db


def test_child_components_use_shared_dependency():
    """Components inside a child module can use the looked-up dependency."""
    app = AppModule()

    result = app.user_module.user_repo.find_user(42)
    assert "SELECT * FROM users WHERE id = 42" in result

    result = app.order_module.order_repo.find_order(7)
    assert "SELECT * FROM orders WHERE id = 7" in result


def test_sibling_modules_share_same_instance():
    """Two child modules both receive the exact same parent instance."""
    app = AppModule()

    user_db = app.user_module.user_repo._db
    order_db = app.order_module.order_repo._db
    assert user_db is order_db
    assert user_db is app.db


def test_lookup_is_noop_on_component():
    """Using lookup on a plain component annotation has no effect.

    The @module factory unwraps lookup[X] to X when processing component
    annotations, so dependency resolution works normally.
    """

    @law_of_demeter("config")
    class ServiceWithLookupAnnotation:
        config: lookup[DatabaseConfig]  # lookup is a no-op on components
        _host: str
        _port: int

        def __init__(self) -> None:
            pass

    @module(CachingStrategy.NOT_THREAD_SAFE)
    class ServiceModule:
        config: DatabaseConfig
        service: ServiceWithLookupAnnotation

    m = ServiceModule()

    # Service still gets its config injected normally
    assert m.service._host == "db.example.com"
    assert m.service._port == 5432


# ---------------------------------------------------------------------------
# Deeper nesting: grandparent → parent → child
# ---------------------------------------------------------------------------


class CacheConfig:
    ttl = 300
    max_size = 1000


@module(CachingStrategy.NOT_THREAD_SAFE)
class CacheModule:
    """Leaf module — looks up db from its parent."""

    db: lookup[DatabaseConnection]
    cache_config: CacheConfig


@module(CachingStrategy.NOT_THREAD_SAFE)
class MiddleModule:
    """Mid-level module — looks up db from *its* parent and passes it down."""

    db: lookup[DatabaseConnection]
    cache_module: CacheModule  # CacheModule's lookup[db] resolves from here


@module(CachingStrategy.NOT_THREAD_SAFE)
class RootModule:
    """Root module — owns the database connection."""

    db: DatabaseConnection
    middle_module: MiddleModule


def test_deeply_nested_lookup():
    """Lookup chains through multiple levels of nesting."""
    root = RootModule()

    assert root.middle_module.db is root.db
    assert root.middle_module.cache_module.db is root.db
    assert root.middle_module.cache_module.cache_config.ttl == 300


# ---------------------------------------------------------------------------
# Renamed lookup: local name differs from parent attribute name
# ---------------------------------------------------------------------------


@module(CachingStrategy.NOT_THREAD_SAFE)
class AuditModule:
    """Child module where the local name differs from the parent's attribute.

    The parent provides ``db``, but this module binds it as ``connection``.
    """

    connection: lookup[DatabaseConnection, "db"]  # noqa: F821  # look up "db" on parent


@module(CachingStrategy.NOT_THREAD_SAFE)
class AppModuleWithRename:
    db: DatabaseConnection
    audit_module: AuditModule


def test_renamed_lookup():
    """lookup[Type, "name"] resolves the parent's attribute under a different local name."""
    app = AppModuleWithRename()

    assert app.audit_module.connection is app.db


@law_of_demeter("_connection")
class AuditService:
    _connection: DatabaseConnection

    def __init__(self) -> None:
        pass

    def log(self) -> str:
        return self._connection.query("INSERT INTO audit_log VALUES (...)")


@module(CachingStrategy.NOT_THREAD_SAFE)
class AuditModuleWithComponent:
    """Renamed lookup feeding into a local component."""

    connection: lookup[DatabaseConnection, "db"]  # noqa: F821
    audit_service: AuditService


@module(CachingStrategy.NOT_THREAD_SAFE)
class AppModuleWithRenameAndComponent:
    db: DatabaseConnection
    audit_module: AuditModuleWithComponent


def test_renamed_lookup_feeds_component():
    """A renamed lookup dependency is visible to child-component factories."""
    app = AppModuleWithRenameAndComponent()

    assert app.audit_module.audit_service._connection is app.db
    result = app.audit_module.audit_service.log()
    assert "INSERT INTO audit_log" in result
