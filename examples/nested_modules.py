"""Example: Nested modules and component-level lookup for parent dependency resolution.

Demonstrates how ``lookup[Type]`` works on both modules and components to
declare dependencies that should be resolved from the parent module rather
than being created locally or forwarded by ``@law_of_demeter``.

**On a module**, ``@module`` skips factory generation and installs a
dict-backed property.  The parent module injects the value lazily through
the dependency-map mechanism.

**On a component**, ``@law_of_demeter`` skips the attribute (does not create
a forwarding property).  The parent module's factory resolves it through the
standard dependency-map mechanism — just like any other injected dependency.

An optional second parameter renames the lookup::

    conn: lookup[DatabaseConnection, "db"]   # look up "db" on parent, bind as "conn"
"""

from typing import cast

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

    # cast() narrows lookup[T] to T — the marker resolves to its inner type at runtime.
    assert cast("DatabaseConnection", app.user_module.db) is app.db
    assert cast("DatabaseConnection", app.order_module.db) is app.db


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


def test_lookup_on_base_ref_unwraps_for_forwarding():
    """lookup on the base_ref is unwrapped so @law_of_demeter can forward properties."""

    @law_of_demeter("config")
    class ServiceWithLookupAnnotation:
        config: lookup[DatabaseConfig]  # unwrapped for type resolution
        _host: str
        _port: int

        def __init__(self) -> None:
            pass

    @module(CachingStrategy.NOT_THREAD_SAFE)
    class ServiceModule:
        config: DatabaseConfig
        service: ServiceWithLookupAnnotation

    m = ServiceModule()

    # Forwarding still works through the unwrapped base_ref type
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

    # lookup[T] resolves to T at runtime — cast() narrows for static analysis.
    assert cast("DatabaseConnection", root.middle_module.db) is root.db
    assert cast("DatabaseConnection", root.middle_module.cache_module.db) is root.db
    assert root.middle_module.cache_module.cache_config.ttl == 300


# ---------------------------------------------------------------------------
# Renamed lookup: local name differs from parent attribute name
# ---------------------------------------------------------------------------


@module(CachingStrategy.NOT_THREAD_SAFE)
class AuditModule:
    """Child module where the local name differs from the parent's attribute.

    The parent provides ``db``, but this module binds it as ``connection``.
    """

    # The two-arg form ``lookup[Type, "name"]`` mixes a type and a string
    # literal — generic classes can't statically express this, so we
    # localise ``# type: ignore[type-arg, name-defined]`` here.
    connection: lookup[DatabaseConnection, "db"]  # type: ignore[type-arg,name-defined] # noqa: F821


@module(CachingStrategy.NOT_THREAD_SAFE)
class AppModuleWithRename:
    db: DatabaseConnection
    audit_module: AuditModule


def test_renamed_lookup():
    """lookup[Type, "name"] resolves the parent's attribute under a different local name."""
    app = AppModuleWithRename()

    # lookup[T, "name"] resolves to T at runtime.
    assert cast("DatabaseConnection", app.audit_module.connection) is app.db


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

    # See note above on the two-arg form requiring ``type: ignore``.
    connection: lookup[DatabaseConnection, "db"]  # type: ignore[type-arg,name-defined] # noqa: F821
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


# ---------------------------------------------------------------------------
# Component-level lookup: lookup works on any component, not just modules
# ---------------------------------------------------------------------------


class Config:
    timeout = 30
    db = "connection_string"  # coincidentally shares a name with DatabaseConnection


@law_of_demeter("_config")
class ServiceWithComponentLookup:
    """Component where _db should come from the parent module, not from config.

    Config has a ``db`` attribute (a string), but ``_db`` is annotated with
    ``lookup[DatabaseConnection]`` so @law_of_demeter skips it.  The parent
    module's factory resolves it from the module's ``db`` attribute instead.
    """

    _config: Config
    _timeout: int  # forwarded from config.timeout
    _db: lookup[DatabaseConnection]  # from parent module, NOT forwarded from config

    def __init__(self) -> None:
        pass

    def do_work(self) -> str:
        # cast() narrows lookup[T] to T at the access site —
        # the marker resolves to its inner type at runtime.
        return cast("DatabaseConnection", self._db).query(f"timeout={self._timeout}")


@module(CachingStrategy.NOT_THREAD_SAFE)
class ComponentLookupModule:
    config: Config
    db: DatabaseConnection
    service: ServiceWithComponentLookup


def test_component_lookup_skips_law_of_demeter_forwarding():
    """lookup on a component prevents @law_of_demeter from forwarding it."""
    m = ComponentLookupModule()

    # _db comes from the module (DatabaseConnection), NOT from config.db (string).
    # cast() narrows lookup[T] to T at the access site.
    assert isinstance(m.service._db, DatabaseConnection)
    assert cast("DatabaseConnection", m.service._db) is m.db
    # _timeout is still forwarded from config
    assert m.service._timeout == 30


def test_component_lookup_with_rename():
    """lookup[Type, "name"] on a component resolves from a renamed parent attribute."""

    @law_of_demeter("_config")
    class ServiceWithRenamedLookup:
        _config: Config
        _timeout: int  # forwarded from config
        # The two-arg form ``lookup[Type, "name"]`` mixes a type and a string
        # literal — generic classes can't statically express this, so we
        # localise ``# type: ignore[type-arg, name-defined]`` here.
        _conn: lookup[DatabaseConnection, "db"]  # type: ignore[type-arg,name-defined] # noqa: F821 — "db" on parent, bound as "_conn"

        def __init__(self) -> None:
            pass

    @module(CachingStrategy.NOT_THREAD_SAFE)
    class RenamedLookupModule:
        config: Config
        db: DatabaseConnection
        service: ServiceWithRenamedLookup

    m = RenamedLookupModule()

    # lookup[T, "name"] resolves to T at runtime.
    assert cast("DatabaseConnection", m.service._conn) is m.db
    assert m.service._timeout == 30


def test_component_lookup_end_to_end():
    """Full end-to-end: component with lookup dependencies works correctly."""
    m = ComponentLookupModule()

    result = m.service.do_work()
    assert "timeout=30" in result
    # lookup[T] resolves to T at runtime — cast() narrows for static analysis.
    assert cast("DatabaseConnection", m.service._db).connected is True
