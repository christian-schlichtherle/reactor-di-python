"""Caching strategies for dependency injection component synthesis.

This module defines caching strategies that control how component instances
are cached and reused within dependency injection modules.
"""

from enum import Enum


class CachingStrategy(Enum):
    """Caching strategy for component synthesis in the dependency injection system.

    Determines how component instances are cached and reused within the module.
    """

    DISABLED = "disabled"
    """No caching - components are created fresh on each access."""

    NOT_THREAD_SAFE = "not_thread_safe"
    """Cache components using @cached_property (not thread-safe but performant)."""
