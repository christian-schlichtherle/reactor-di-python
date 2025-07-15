"""Caching strategies example for reactor-di.

This example demonstrates the different caching strategies available:
- CachingStrategy.DISABLED: Components created fresh each time
- CachingStrategy.NOT_THREAD_SAFE: Cached components (same instance returned)
"""

from reactor_di import CachingStrategy, module


class MyService:
    """Example service to demonstrate caching behavior."""

    def __init__(self):
        self.instance_id = id(self)

    def get_instance_id(self) -> int:
        """Return the instance ID for testing caching behavior."""
        return self.instance_id


# No caching - components created fresh each time
@module(CachingStrategy.DISABLED)
class DevModule:
    """Development module with no caching."""

    service: MyService


# Cached components - same instance returned (not thread-safe)
@module(CachingStrategy.NOT_THREAD_SAFE)
class ProdModule:
    """Production module with caching enabled."""

    service: MyService


def test_disabled_caching():
    """Test that DISABLED strategy creates fresh instances each time."""
    dev_module = DevModule()

    # Get service multiple times
    service1 = dev_module.service
    service2 = dev_module.service
    service3 = dev_module.service

    # Each call should return a different instance
    assert service1 is not service2
    assert service2 is not service3
    assert service1 is not service3

    # Instance IDs should be different
    assert service1.get_instance_id() != service2.get_instance_id()
    assert service2.get_instance_id() != service3.get_instance_id()


def test_not_thread_safe_caching():
    """Test that NOT_THREAD_SAFE strategy caches instances."""
    prod_module = ProdModule()

    # Get service multiple times
    service1 = prod_module.service
    service2 = prod_module.service
    service3 = prod_module.service

    # All calls should return the same instance
    assert service1 is service2
    assert service2 is service3
    assert service1 is service3

    # Instance IDs should be the same
    assert service1.get_instance_id() == service2.get_instance_id()
    assert service2.get_instance_id() == service3.get_instance_id()


def test_different_modules_have_different_instances():
    """Test that different module instances have different cached services."""
    prod_module1 = ProdModule()
    prod_module2 = ProdModule()

    service1 = prod_module1.service
    service2 = prod_module2.service

    # Different module instances should have different service instances
    assert service1 is not service2
    assert service1.get_instance_id() != service2.get_instance_id()


def test_caching_strategy_comparison():
    """Test that different caching strategies behave differently."""
    dev_module = DevModule()
    prod_module = ProdModule()

    # Test dev module (no caching)
    dev_service1 = dev_module.service
    dev_service2 = dev_module.service
    assert dev_service1 is not dev_service2  # Different instances

    # Test prod module (with caching)
    prod_service1 = prod_module.service
    prod_service2 = prod_module.service
    assert prod_service1 is prod_service2  # Same instance
