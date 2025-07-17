"""Caching strategies example for reactor-di.

This example demonstrates the different caching strategies available:
- CachingStrategy.DISABLED: Components created fresh each time
- CachingStrategy.NOT_THREAD_SAFE: Cached components (same instance returned)
"""

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
