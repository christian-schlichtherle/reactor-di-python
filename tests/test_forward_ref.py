"""Regression tests for TYPE_CHECKING forward reference handling.

These tests reproduce the bug where module factory calls get_type_hints()
on a component class that uses `if TYPE_CHECKING:` imports to avoid circular
dependencies.  With `from __future__ import annotations`, all annotations
become strings.  get_type_hints() then fails with NameError for types only
imported under TYPE_CHECKING.
"""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from reactor_di import CachingStrategy, law_of_demeter, module

if TYPE_CHECKING:
    # This class is NOT available at runtime (TYPE_CHECKING is False).
    # Simulates the pattern: `from other_module import SomeClass` inside
    # an `if TYPE_CHECKING:` block to avoid circular imports.
    class TypeCheckOnlyService:
        pass


class SimpleConfig:
    host: str
    port: int

    def __init__(self, **kwargs: object) -> None:
        for key, value in kwargs.items():
            object.__setattr__(self, key, value)


@law_of_demeter("_config")
class BaseController:
    _config: SimpleConfig
    _host: str
    _port: int

    def __init__(self) -> None:
        pass

    def address(self) -> str:
        return f"{self._host}:{self._port}"


class ControllerWithForwardRef(BaseController):
    """Controller with a TYPE_CHECKING-only forward reference annotation.

    Mimics the dsctl pattern where DruidIngestionController adds
    `_port_forward: DruidPortForwardController` using a TYPE_CHECKING import.
    """

    _special: TypeCheckOnlyService


@module(CachingStrategy.NOT_THREAD_SAFE)
class ForwardRefModule:
    controller: ControllerWithForwardRef

    @cached_property
    def config(self) -> SimpleConfig:
        return SimpleConfig(host="localhost", port=8080)

    def __init__(self) -> None:
        pass


def test_forward_ref_does_not_crash_factory():
    """Module factory must handle TYPE_CHECKING forward references gracefully."""
    mod = ForwardRefModule()
    ctrl = mod.controller

    assert ctrl._config is mod.config
    assert ctrl._host == "localhost"
    assert ctrl._port == 8080
    assert ctrl.address() == "localhost:8080"
