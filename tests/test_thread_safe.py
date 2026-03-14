"""Regression tests for CachingStrategy.THREAD_SAFE.

Tests that the thread-safe caching strategy guarantees singleton behavior
for dependency injection components under concurrent access, including
both the cached property descriptor and lazy _module_getattr resolution.
"""

from __future__ import annotations

import threading
from functools import cached_property

from reactor_di import CachingStrategy, law_of_demeter, module

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class SimpleService:
    pass


class CountingService:
    """Service that counts how many instances have been created."""

    _counter_lock = threading.Lock()
    _instance_count = 0

    def __init__(self) -> None:
        with CountingService._counter_lock:
            CountingService._instance_count += 1


class Config:
    def __init__(self) -> None:
        self.host = "localhost"
        self.port = 8080


@law_of_demeter("_config")
class Controller:
    _config: Config
    _host: str
    _port: int

    def __init__(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Modules
# ---------------------------------------------------------------------------


@module(CachingStrategy.THREAD_SAFE)
class ThreadSafeModule:
    service: SimpleService


@module(CachingStrategy.THREAD_SAFE)
class ThreadSafeCountingModule:
    service: CountingService


@module(CachingStrategy.THREAD_SAFE)
class ThreadSafeControllerModule:
    controller: Controller

    @cached_property
    def config(self) -> Config:
        return Config()


@module(CachingStrategy.NOT_THREAD_SAFE)
class NotThreadSafeModule:
    service: SimpleService


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_basic_cached_behavior():
    """Thread-safe cached property returns the same instance on repeated access."""
    mod = ThreadSafeModule()

    service1 = mod.service
    service2 = mod.service
    service3 = mod.service

    assert service1 is service2
    assert service2 is service3


def test_concurrent_access_single_instantiation():
    """N threads racing to access the same component get the same instance."""
    CountingService._instance_count = 0
    mod = ThreadSafeCountingModule()
    num_threads = 20
    results: list = []
    barrier = threading.Barrier(num_threads)

    def access_service() -> None:
        barrier.wait()
        results.append(mod.service)

    threads = [threading.Thread(target=access_service) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == num_threads
    assert all(r is results[0] for r in results)
    assert CountingService._instance_count == 1


def test_different_module_instances_have_independent_caches():
    """Different module instances produce different component instances."""
    mod1 = ThreadSafeModule()
    mod2 = ThreadSafeModule()

    service1 = mod1.service
    service2 = mod2.service

    assert service1 is not service2
    # But each is cached within its own module
    assert mod1.service is service1
    assert mod2.service is service2


def test_thread_safe_module_getattr_concurrent():
    """Concurrent access to lazy-resolved dependencies on components is safe."""
    mod = ThreadSafeControllerModule()
    num_threads = 20
    results: list = []
    barrier = threading.Barrier(num_threads)

    def access_controller_config() -> None:
        barrier.wait()
        controller = mod.controller
        # _config is resolved lazily via _module_getattr
        results.append(controller._config)

    threads = [
        threading.Thread(target=access_controller_config) for _ in range(num_threads)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == num_threads
    # All threads should get the same config instance
    assert all(r is results[0] for r in results)


def test_mixed_strategies():
    """A THREAD_SAFE module and a NOT_THREAD_SAFE module coexist."""
    ts_mod = ThreadSafeModule()
    nts_mod = NotThreadSafeModule()

    ts_service1 = ts_mod.service
    ts_service2 = ts_mod.service
    nts_service1 = nts_mod.service
    nts_service2 = nts_mod.service

    # Thread-safe: same instance
    assert ts_service1 is ts_service2
    # Not thread-safe: also cached (cached_property)
    assert nts_service1 is nts_service2
    # But they are independent
    assert ts_service1 is not nts_service1


def test_class_access_returns_descriptor():
    """Accessing the property on the class (not instance) returns the descriptor."""
    descriptor = ThreadSafeModule.__dict__["service"]
    assert hasattr(descriptor, "__get__")
    assert hasattr(descriptor, "__set_name__")


def test_thread_safe_with_law_of_demeter_forwarding():
    """Thread-safe module works with law_of_demeter forwarded properties."""
    mod = ThreadSafeControllerModule()
    controller = mod.controller

    assert controller._host == "localhost"
    assert controller._port == 8080
    assert controller._config is mod.config
