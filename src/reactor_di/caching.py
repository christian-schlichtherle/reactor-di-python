"""Caching strategies for dependency injection component synthesis.

This module defines caching strategies that control how component instances
are cached and reused within dependency injection modules.
"""

from __future__ import annotations

import threading
from enum import Enum
from typing import Any, Callable, Type


class CachingStrategy(Enum):
    """Caching strategy for component synthesis in the dependency injection system.

    Determines how component instances are cached and reused within the module.
    """

    DISABLED = "disabled"
    """No caching - components are created fresh on each access."""

    NOT_THREAD_SAFE = "not_thread_safe"
    """Cache components using @cached_property (not thread-safe but performant)."""

    THREAD_SAFE = "thread_safe"
    """Cache components using a thread-safe descriptor with per-instance locking."""


class thread_safe_cached_property:
    """A cached property descriptor with per-instance, per-attribute locking.

    Uses double-checked locking to ensure the factory runs exactly once per
    instance, even under concurrent access from multiple threads.
    """

    def __class_getitem__(cls, item: Any) -> Any:
        return cls

    def __init__(self, func: Callable[..., Any]) -> None:
        self.func = func
        self.attr_name: str = ""
        self.lock_name: str = ""

    def __set_name__(self, owner: Type[Any], name: str) -> None:
        self.attr_name = name
        self.lock_name = f"_lock_{name}"

    def __get__(self, instance: Any, owner: Type[Any] | None = None) -> Any:
        if instance is None:
            return self
        # Fast path: already cached in instance dict
        try:
            return instance.__dict__[self.attr_name]
        except KeyError:
            pass
        # Slow path: acquire per-instance, per-attribute lock
        lock = instance.__dict__.setdefault(self.lock_name, threading.Lock())
        with lock:
            # Double-check after acquiring lock
            try:
                return instance.__dict__[self.attr_name]
            except KeyError:
                pass
            value = self.func(instance)
            instance.__dict__[self.attr_name] = value
            return value
