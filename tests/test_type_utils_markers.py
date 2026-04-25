"""Unit tests for ``lookup`` / ``make`` runtime markers.

Covers the runtime-only invariants that the example-based tests don't reach:

* The marker classes are callable (a hard requirement for
  ``typing._type_check`` on Python 3.9 / 3.10) but raise ``TypeError``
  if anyone actually invokes them.
* ``lookup`` and ``make`` cannot be instantiated or subclassed.
* ``__repr__`` produces a stable, recognizable string.
"""

from __future__ import annotations

import pytest

from reactor_di import lookup, make
from reactor_di.type_utils import _LookupMarker, _MakeMarker


class TestLookupMarker:
    def test_subscript_returns_marker(self) -> None:
        marker = lookup[str]
        assert isinstance(marker, _LookupMarker)
        assert marker.inner_type is str
        assert marker.source_name is None

    def test_subscript_with_rename(self) -> None:
        marker = lookup[str, "alt"]
        assert isinstance(marker, _LookupMarker)
        assert marker.inner_type is str
        assert marker.source_name == "alt"

    def test_repr(self) -> None:
        assert repr(lookup[str]) == "lookup[str]"
        assert repr(lookup[int, "x"]) == 'lookup[int, "x"]'

    def test_marker_is_callable_for_type_check_compatibility(self) -> None:
        # ``typing._type_check`` on Py3.9/3.10 falls through to ``callable(arg)``
        # for non-class annotation values, so marker instances must be callable.
        marker = lookup[str]
        assert callable(marker)

    def test_calling_marker_raises(self) -> None:
        marker = lookup[str]
        with pytest.raises(TypeError, match="not callable"):
            marker()

    def test_lookup_class_not_instantiable(self) -> None:
        with pytest.raises(TypeError, match="not instantiable"):
            lookup()

    def test_lookup_class_not_subclassable(self) -> None:
        with pytest.raises(TypeError, match="cannot be subclassed"):

            class _Sub(lookup):
                pass


class TestMakeMarker:
    def test_subscript_returns_marker(self) -> None:
        marker = make[str, int]
        assert isinstance(marker, _MakeMarker)
        assert marker.base_type is str
        assert marker.impl_type is int

    def test_repr(self) -> None:
        assert repr(make[str, int]) == "make[str, int]"

    def test_subscript_requires_two_params(self) -> None:
        with pytest.raises(TypeError, match="exactly two type parameters"):
            make[str]
        with pytest.raises(TypeError, match="exactly two type parameters"):
            make[str, int, float]  # type: ignore[misc]

    def test_marker_is_callable_for_type_check_compatibility(self) -> None:
        marker = make[str, int]
        assert callable(marker)

    def test_calling_marker_raises(self) -> None:
        marker = make[str, int]
        with pytest.raises(TypeError, match="not callable"):
            marker()

    def test_make_class_not_instantiable(self) -> None:
        with pytest.raises(TypeError, match="not instantiable"):
            make()

    def test_make_class_not_subclassable(self) -> None:
        with pytest.raises(TypeError, match="cannot be subclassed"):

            class _Sub(make):
                pass
