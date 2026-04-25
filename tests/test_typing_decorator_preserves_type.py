"""Static-typing regression test: decorators must preserve the input class type.

This file is intentionally minimal at runtime — its real purpose is to be
checked by ``mypy``.  If ``law_of_demeter`` or ``module`` regress to a
``Callable[[type[Any]], type[Any]]`` signature (which erases the input
class type), the ``assert_type`` calls below will fail static type
checking, even though the runtime ``test_*`` function will still pass.

The runtime ``test_*`` functions exist so that pytest does not warn about
the file containing only declarations.

Mypy is wired to check this file via the project's mypy invocation (see
``CLAUDE.md`` / CI config).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from reactor_di import CachingStrategy, law_of_demeter, module

if TYPE_CHECKING:
    # ``typing.assert_type`` was added in Python 3.11; the project's mypy is
    # pinned to ``python_version = "3.9"``, so we import from typing_extensions,
    # whose stubs are always available to mypy.  The runtime stub below makes
    # this work in pytest without adding a runtime dependency.
    from typing_extensions import assert_type
else:

    def assert_type(val: object, _typ: object) -> object:
        """Runtime no-op stub mirroring ``typing.assert_type``."""
        return val


# --- Sample classes used as fixtures for the type assertions ---------------


class _Base:
    """Plain base used to verify ``@module``-decorated classes keep their type."""

    config: _Config


class _Config:
    """Plain dependency used by ``_LoD`` and ``_Base``."""

    timeout: int = 30


class _LoD:
    """Plain class used to verify ``@law_of_demeter`` keeps its type.

    The ``_x`` annotation references ``_Config`` so the decorator finds at
    least one resolvable forwardable attribute.
    """

    _x: _Config


# --- Type-level assertions -------------------------------------------------


# law_of_demeter: TypeVar-bound decorator must preserve the class type.
DecoratedLoD = law_of_demeter("_x")(_LoD)
assert_type(DecoratedLoD, type[_LoD])


# module bare: @module on a class should return the same class type.
DecoratedBare = module(_Base)
assert_type(DecoratedBare, type[_Base])


# module with strategy: @module(CachingStrategy.X) returns Callable[[_C], _C].
_with_strategy = module(CachingStrategy.NOT_THREAD_SAFE)
DecoratedWithStrategy = _with_strategy(_Base)
assert_type(DecoratedWithStrategy, type[_Base])


# module with empty parens: @module() also returns Callable[[_C], _C].
_empty = module()
DecoratedEmpty = _empty(_Base)
assert_type(DecoratedEmpty, type[_Base])


# --- Runtime sanity checks -------------------------------------------------


def test_law_of_demeter_returns_class_at_runtime() -> None:
    assert DecoratedLoD is _LoD


def test_module_bare_returns_class_at_runtime() -> None:
    assert DecoratedBare is _Base


def test_module_with_strategy_returns_class_at_runtime() -> None:
    assert DecoratedWithStrategy is _Base


def test_module_empty_returns_class_at_runtime() -> None:
    assert DecoratedEmpty is _Base
