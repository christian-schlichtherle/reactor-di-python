"""Caching strategies example for reactor-di.

This example demonstrates the different caching strategies available:
- CachingStrategy.DISABLED: Components created fresh each time
- CachingStrategy.NOT_THREAD_SAFE: Cached components (same instance returned)
- CachingStrategy.THREAD_SAFE: Cached components with thread-safe singleton guarantee
"""

import threading

from reactor_di import CachingStrategy, module


class ServiceMock:
    pass


# No caching - components created fresh each time
@module
class DefaultModule:
    service: ServiceMock


# No caching - components created fresh each time
@module(CachingStrategy.DISABLED)
class FactoryModule:
    service: ServiceMock


# Cached components - same instance returned (not thread-safe)
@module(CachingStrategy.NOT_THREAD_SAFE)
class SingletonModule:
    service: ServiceMock


def test_disabled_caching():
    """Test that DISABLED strategy creates fresh instances each time."""

    for factory_module in (DefaultModule(), FactoryModule()):
        # Get service multiple times
        service1 = factory_module.service
        service2 = factory_module.service
        service3 = factory_module.service

        # Each call should return a different instance
        assert service1 is not service2
        assert service2 is not service3
        assert service3 is not service1


def test_not_thread_safe_caching():
    """Test that NOT_THREAD_SAFE strategy caches instances."""

    singleton_module = SingletonModule()

    # Get service multiple times
    service1 = singleton_module.service
    service2 = singleton_module.service
    service3 = singleton_module.service

    # All calls should return the same instance
    assert service1 is service2
    assert service2 is service3
    assert service3 is service1


def test_different_modules_have_different_instances():
    """Test that different module instances have different cached services."""

    singleton_module1 = SingletonModule()
    singleton_module2 = SingletonModule()

    service1 = singleton_module1.service
    service2 = singleton_module2.service

    # Different module instances should have different service instances
    assert service1 is not service2


class CountingService:
    """Service that counts how many instances have been created."""

    _counter_lock = threading.Lock()
    _instance_count = 0

    def __init__(self) -> None:
        with CountingService._counter_lock:
            CountingService._instance_count += 1


@module(CachingStrategy.THREAD_SAFE)
class CountingModule:
    service: CountingService


def test_thread_safe_caching():
    """Test that THREAD_SAFE strategy caches instances."""

    CountingService._instance_count = 0
    ts_module = CountingModule()

    service1 = ts_module.service
    service2 = ts_module.service
    service3 = ts_module.service

    # All calls should return the same instance
    assert service1 is service2
    assert service2 is service3
    assert CountingService._instance_count == 1


def test_thread_safe_concurrent_access():
    """Test that concurrent access creates exactly one instance."""

    CountingService._instance_count = 0
    ts_module = CountingModule()
    results: list[CountingService] = []
    barrier = threading.Barrier(10)

    def access_service() -> None:
        barrier.wait()
        results.append(ts_module.service)

    threads = [threading.Thread(target=access_service) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All threads should get the same instance
    assert all(r is results[0] for r in results)
    # Factory should have run exactly once
    assert CountingService._instance_count == 1
