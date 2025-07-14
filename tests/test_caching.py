"""Comprehensive tests for caching strategy enum."""

# type: ignore

import pytest

from src.reactor_di.caching import CachingStrategy


class TestCachingStrategy:
    """Test CachingStrategy enum."""

    def test_enum_values(self):
        """Test enum has correct values."""
        assert CachingStrategy.DISABLED.value == "disabled"
        assert CachingStrategy.NOT_THREAD_SAFE.value == "not_thread_safe"
