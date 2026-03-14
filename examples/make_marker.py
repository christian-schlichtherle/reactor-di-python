"""Example: Subtype factory generation with ``make[BaseType, ImplType]``.

Demonstrates how ``make`` lets you program to an interface (abstract base
class or protocol) while the module factory instantiates a concrete
implementation behind the scenes.

The generated factory is equivalent to::

    @cached_property
    def service(self) -> ServiceBase:
        return ServiceImpl()

This is useful for:
- Swapping implementations without changing the module's public API
- Programming against abstract types while keeping concrete wiring in one place
- Combining with ``@law_of_demeter`` where the base_ref type is abstract
"""

from abc import ABC, abstractmethod

from reactor_di import CachingStrategy, law_of_demeter, make, module

# ---------------------------------------------------------------------------
# Base types (interfaces) and concrete implementations
# ---------------------------------------------------------------------------


class Logger(ABC):
    @abstractmethod
    def log(self, message: str) -> str: ...


class ConsoleLogger(Logger):
    def log(self, message: str) -> str:
        return f"[console] {message}"


class FileLogger(Logger):
    def log(self, message: str) -> str:
        return f"[file] {message}"


class Cache(ABC):
    @abstractmethod
    def get(self, key: str) -> str | None: ...


class InMemoryCache(Cache):
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)


# ---------------------------------------------------------------------------
# Basic usage: module with make annotations
# ---------------------------------------------------------------------------


@module(CachingStrategy.NOT_THREAD_SAFE)
class AppModule:
    """Module that wires abstract types to concrete implementations."""

    logger: make[Logger, ConsoleLogger]
    cache: make[Cache, InMemoryCache]


def test_make_creates_impl_type():
    """The factory instantiates the implementation type, not the base type."""
    app = AppModule()

    assert isinstance(app.logger, ConsoleLogger)
    assert isinstance(app.logger, Logger)
    assert app.logger.log("hello") == "[console] hello"


def test_make_creates_impl_type_for_cache():
    """Another make annotation, verifying the concrete type is used."""
    app = AppModule()

    assert isinstance(app.cache, InMemoryCache)
    assert isinstance(app.cache, Cache)
    assert app.cache.get("missing") is None


def test_make_caching_returns_same_instance():
    """Caching works normally — repeated access returns the same instance."""
    app = AppModule()

    assert app.logger is app.logger
    assert app.cache is app.cache


# ---------------------------------------------------------------------------
# Swapping implementations: same module shape, different wiring
# ---------------------------------------------------------------------------


@module(CachingStrategy.NOT_THREAD_SAFE)
class AppModuleWithFileLogger:
    """Same structure as AppModule but wired to FileLogger."""

    logger: make[Logger, FileLogger]
    cache: make[Cache, InMemoryCache]


def test_swap_implementation():
    """Changing the impl type changes what the factory creates."""
    app = AppModuleWithFileLogger()

    assert isinstance(app.logger, FileLogger)
    assert app.logger.log("hello") == "[file] hello"


# ---------------------------------------------------------------------------
# make + dependency injection into the created component
# ---------------------------------------------------------------------------


class Config:
    retry_count = 3
    base_url = "https://api.example.com"


@law_of_demeter("_config")
class ServiceBase(ABC):
    _config: Config
    _retry_count: int
    _base_url: str

    @abstractmethod
    def call(self) -> str: ...


class HttpService(ServiceBase):
    def call(self) -> str:
        return f"GET {self._base_url} (retries={self._retry_count})"


@module(CachingStrategy.NOT_THREAD_SAFE)
class ServiceModule:
    """The factory creates HttpService, and DI injects config into it."""

    config: Config
    service: make[ServiceBase, HttpService]


def test_make_with_dependency_injection():
    """Dependencies are injected into the impl type created by make."""
    m = ServiceModule()

    assert isinstance(m.service, HttpService)
    assert m.service._config is m.config
    assert m.service.call() == "GET https://api.example.com (retries=3)"


def test_make_with_law_of_demeter_forwarding():
    """@law_of_demeter forwarding works on the impl type."""
    m = ServiceModule()

    assert m.service._retry_count == 3
    assert m.service._base_url == "https://api.example.com"


# ---------------------------------------------------------------------------
# make with DISABLED caching (new instance each time)
# ---------------------------------------------------------------------------


@module(CachingStrategy.DISABLED)
class TransientModule:
    logger: make[Logger, ConsoleLogger]


def test_make_with_disabled_caching():
    """With DISABLED caching, each access creates a new instance."""
    m = TransientModule()

    logger1 = m.logger
    logger2 = m.logger

    assert isinstance(logger1, ConsoleLogger)
    assert logger1 is not logger2
