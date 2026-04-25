"""Example: ``lookup[T]`` and ``make[B, I]`` erase to ``T`` / ``B`` for type checkers.

Regression test for the bug introduced in 0.5.1 where ``lookup`` and ``make``
were declared as ``Generic[_T]`` / ``Generic[_B, _I]`` subclasses.  That made
attribute access on them statically typed as ``lookup[T]`` / ``make[B, I]``
instances, breaking every consumer that expected the inner type — e.g.::

    self.group_id + "-changelog"      # "lookup has no __add__"
    await self.state_store.restore()  # "Unresolved attribute reference 'restore'"

The fix mirrors the static behavior of :data:`typing.Final` and
:data:`typing.ClassVar`: under ``TYPE_CHECKING``, ``lookup`` and ``make`` are
generic type aliases (built with :class:`typing_extensions.TypeAliasType`)
that strip the metadata and present the inner type to static analyzers.
At runtime they remain the marker classes whose ``__class_getitem__``
produces ``_LookupMarker`` / ``_MakeMarker`` instances consumed by the
``@module`` decorator.

The static guarantees below are evaluated by ``mypy`` and ``pyright`` in CI
(``uv run mypy src examples``); a regression to a ``Generic[...]``-style
declaration would fail these assertions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from reactor_di import CachingStrategy, law_of_demeter, lookup, make, module

if TYPE_CHECKING:
    from typing_extensions import assert_type
else:

    def assert_type(val: object, _typ: object) -> object:
        """Runtime no-op stub mirroring ``typing.assert_type``."""
        return val


# --- Fixtures --------------------------------------------------------------


class _StateStore:
    """Stand-in for the StateStore consumers see in real DI modules."""

    async def restore(self) -> None:
        return None

    async def close(self) -> None:
        return None


class _ChangelogStateStore(_StateStore):
    """Subtype used as the ``Impl`` argument of ``make[Base, Impl]``."""


class _Config:
    timeout: int = 30


# --- Static + runtime: lookup[T] erases to T -------------------------------


@module(CachingStrategy.NOT_THREAD_SAFE)
class _LookupModule:
    """Concrete reproduction of the fret-datasources/fretworx pattern."""

    group_id: lookup[str]
    client_id: lookup[str]
    bootstrap_servers: lookup[str]
    config: _Config

    def derived_topic(self) -> str:
        # Regression: ``self.group_id + "-changelog"`` must type-check as
        # ``str + str``.  Under the 0.5.1 bug, mypy would report
        # "Class 'lookup' does not define '__add__'".
        topic = self.group_id + "-changelog"
        assert_type(topic, str)
        return topic


# --- Static + runtime: make[B, I] erases to B ------------------------------


@module(CachingStrategy.NOT_THREAD_SAFE)
class _MakeModule:
    state_store: make[_StateStore, _ChangelogStateStore]


def _consume_make_module(m: _MakeModule) -> _StateStore:
    # Regression: must resolve ``.restore`` and ``.close`` on
    # ``self.state_store``.  Under the 0.5.1 bug, mypy reported
    # "Unresolved attribute reference 'restore' for class 'make'".
    assert_type(m.state_store, _StateStore)
    return m.state_store


# --- Static-only assertions on bare annotations ----------------------------


# We assert the erased static type of access expressions using assert_type
# inside a function — module-level assert_type doesn't see the descriptor
# semantics installed by ``@module``.
def _static_only_assertions() -> None:
    m = _LookupModule()
    assert_type(m.group_id, str)
    assert_type(m.client_id, str)
    assert_type(m.bootstrap_servers, str)

    mm = _MakeModule()
    assert_type(mm.state_store, _StateStore)


# --- Runtime sanity --------------------------------------------------------


def test_lookup_attribute_concatenation_at_runtime() -> None:
    m = _LookupModule()
    m.group_id = "group"
    m.client_id = "client"
    m.bootstrap_servers = "localhost:9092"
    assert m.derived_topic() == "group-changelog"


def test_make_attribute_at_runtime() -> None:
    m = _MakeModule()
    assert isinstance(m.state_store, _ChangelogStateStore)
    assert isinstance(m.state_store, _StateStore)


@law_of_demeter("_config")
class _Component:
    _config: _Config
    _timeout: int  # forwarded from _config.timeout
    _store: lookup[_StateStore]  # from parent module

    def __init__(self) -> None:
        pass

    def get_timeout(self) -> int:
        # ``self._timeout`` is statically int — direct return type-checks.
        return self._timeout


@module(CachingStrategy.NOT_THREAD_SAFE)
class _CompModule:
    config: _Config
    store: _StateStore
    component: _Component


def test_law_of_demeter_with_lookup() -> None:
    """Component-level ``lookup`` still erases to ``T`` for type checkers."""
    m = _CompModule()
    assert m.component.get_timeout() == 30
    assert m.component._store is m.store
