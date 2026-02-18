"""Regression tests for lazy per-attribute dependency resolution.

These tests reproduce bugs found when module cached properties depend on
deferred initialization (e.g., attributes set in __aenter__ for async
context managers).  The old eager setup_dependencies() resolved ALL
dependencies at once, causing AttributeError for properties not yet
available.  The fix resolves each dependency individually on first access.
"""

from functools import cached_property

import pytest

from reactor_di import CachingStrategy, law_of_demeter, module


class AnnotationOnlyConfig:
    """Config class where fields are annotations without class-level attributes.

    Mimics Pydantic BaseSettings/BaseModel behavior.
    """

    destination_topic_prefix: str
    events_queue: str
    host: str
    port: int
    timeout: int

    def __init__(self, **kwargs: object) -> None:
        for key, value in kwargs.items():
            object.__setattr__(self, key, value)


class ExternalApi:
    """Represents an external resource requiring deferred initialization."""

    def call(self) -> str:
        return "api-response"


@law_of_demeter("_config")
class DeferredController:
    """Controller with both immediate and deferred dependencies.

    _config and forwarded properties (_host, _timeout) are available immediately.
    _api and _namespace depend on module properties that require deferred init.
    """

    _api: ExternalApi
    _config: AnnotationOnlyConfig
    _host: str  # forwarded from config
    _timeout: int  # forwarded from config
    _namespace: str  # from module, not from config

    def __init__(self) -> None:
        pass

    def status(self) -> str:
        return f"{self._host}:{self._timeout}"


@module(CachingStrategy.NOT_THREAD_SAFE)
class DeferredModule:
    """Module where some cached properties depend on deferred initialization.

    Mimics the pattern where __init__ sets _config, but _api and _namespace
    are only set later (e.g., in __aenter__ for async context managers).
    """

    controller: DeferredController

    @cached_property
    def api(self) -> ExternalApi:
        return self._api  # type: ignore[attr-defined]

    @cached_property
    def config(self) -> AnnotationOnlyConfig:
        return self._config  # type: ignore[attr-defined]

    @cached_property
    def namespace(self) -> str:
        return self._namespace  # type: ignore[attr-defined]

    def __init__(self, config: AnnotationOnlyConfig) -> None:
        self._config = config

    def initialize(self) -> None:
        """Simulate __aenter__ / deferred initialization."""
        self._api = ExternalApi()
        self._namespace = "test-ns"


def test_lazy_resolution_immediate_deps_before_deferred_init():
    """Accessing immediately-available deps must work before deferred init.

    This reproduces the dsctl bug: accessing controller._config triggers
    eager resolution of ALL dependencies including _api and _namespace,
    which depend on module properties not yet initialized.
    """
    config = AnnotationOnlyConfig(
        destination_topic_prefix="test-",
        events_queue="events",
        host="localhost",
        port=6379,
        timeout=300,
    )
    mod = DeferredModule(config)

    controller = mod.controller

    # These should work - _config is available via module.__init__
    assert controller._config is config

    # Forwarded properties from config should work too
    assert controller._host == "localhost"
    assert controller._timeout == 300
    assert controller.status() == "localhost:300"


def test_lazy_resolution_all_deps_after_deferred_init():
    """All deps should work after deferred init completes."""
    config = AnnotationOnlyConfig(
        destination_topic_prefix="test-",
        events_queue="events",
        host="localhost",
        port=6379,
        timeout=300,
    )
    mod = DeferredModule(config)
    mod.initialize()

    controller = mod.controller

    assert controller._config is config
    assert controller._api is mod.api
    assert controller._namespace == "test-ns"
    assert controller._host == "localhost"


def test_lazy_resolution_deferred_dep_before_init_raises():
    """Accessing deferred deps before init should raise AttributeError."""
    config = AnnotationOnlyConfig(
        destination_topic_prefix="test-",
        events_queue="events",
        host="localhost",
        port=6379,
        timeout=300,
    )
    mod = DeferredModule(config)

    controller = mod.controller

    # _api depends on module.api which returns self._api (not set yet)
    with pytest.raises(AttributeError):
        _ = controller._api

    # After init, it should work
    mod.initialize()
    assert controller._api is mod.api
