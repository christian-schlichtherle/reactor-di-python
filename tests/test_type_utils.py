"""Comprehensive tests for type_utils module - targeting 100% coverage with disjunct test cases."""

# type: ignore

from abc import ABC, abstractmethod
from functools import cached_property
from typing import Dict, Any
from unittest.mock import Mock

import pytest

from src.reactor_di.type_utils import (
    is_type_compatible,
    safe_get_type_hints,
    get_all_type_hints,
    needs_implementation,
)


class TestIsTypeCompatible:
    """Disjunct tests for is_type_compatible - each test targets specific code paths."""

    def test_string_annotations_matching(self):
        """Test exact string match path."""
        assert is_type_compatible("MyClass", "MyClass")

    def test_string_annotations_not_matching(self):
        """Test string mismatch path."""
        assert not is_type_compatible("ClassA", "ClassB")

    def test_mixed_string_and_type_name_based(self):
        """Test name-based comparison with mixed types."""

        class MyClass:
            pass

        assert is_type_compatible("MyClass", MyClass)
        assert is_type_compatible(MyClass, "MyClass")

    def test_none_types_equal(self):
        """Test None == None path."""
        assert is_type_compatible(None, None)

    def test_none_types_not_equal(self):
        """Test None != other type path."""
        assert not is_type_compatible(None, str)
        assert not is_type_compatible(str, None)

    def test_subclass_relationship_valid(self):
        """Test valid subclass path."""

        class Parent:
            pass

        class Child(Parent):
            pass

        assert is_type_compatible(Child, Parent)

    def test_subclass_relationship_invalid(self):
        """Test invalid subclass path."""

        class Parent:
            pass

        class Child(Parent):
            pass

        assert not is_type_compatible(Parent, Child)

    def test_exact_type_match(self):
        """Test exact type equality path."""
        assert is_type_compatible(str, str)
        assert is_type_compatible(int, int)

    def test_issubclass_type_error_fallback(self):
        """Test TypeError handling in issubclass - conservative True fallback."""
        # Create mock type that causes TypeError in issubclass
        mock_type = Mock()
        mock_type.__name__ = "MockType"

        # This should trigger TypeError and fallback to True
        assert is_type_compatible(mock_type, str) is True

    def test_conservative_fallback_for_complex_types(self):
        """Test conservative True fallback for unhandled types."""
        from typing import Union

        # Complex types should fallback to True
        assert is_type_compatible(Union[str, int], Union[str, int])


class TestSafeGetTypeHints:
    """Disjunct tests for safe_get_type_hints function."""

    def test_successful_get_type_hints(self):
        """Test successful type hints retrieval."""

        class TestClass:
            attr: str

        hints = safe_get_type_hints(TestClass)
        assert hints == {"attr": str}

    def test_name_error_fallback_to_annotations(self):
        """Test NameError fallback to __annotations__."""

        class BadAnnotations:
            # This will cause NameError in get_type_hints
            attr: "NonexistentType"

        hints = safe_get_type_hints(BadAnnotations)
        assert hints == {"attr": "NonexistentType"}

    def test_no_annotations_attribute(self):
        """Test class without __annotations__ attribute."""

        class NoAnnotations:
            pass

        # Remove annotations if they exist
        if hasattr(NoAnnotations, "__annotations__"):
            delattr(NoAnnotations, "__annotations__")

        hints = safe_get_type_hints(NoAnnotations)
        assert hints == {}


class TestGetAllTypeHints:
    """Disjunct tests for get_all_type_hints function."""

    def test_single_class_hints(self):
        """Test type hints from single class."""

        class SingleClass:
            attr: str

        hints = get_all_type_hints(SingleClass)
        assert hints == {"attr": str}

    def test_inheritance_hierarchy_hints(self):
        """Test type hints collection from inheritance hierarchy."""

        class Base:
            base_attr: str

        class Child(Base):
            child_attr: int

        hints = get_all_type_hints(Child)
        assert "base_attr" in hints
        assert "child_attr" in hints
        assert hints["base_attr"] == str
        assert hints["child_attr"] == int

    def test_overridden_annotations(self):
        """Test child class annotations override parent ones."""

        class Parent:
            attr: str

        class Child(Parent):
            attr: int  # Override parent annotation

        hints = get_all_type_hints(Child)
        assert hints["attr"] == int  # Child should override

    def test_skip_object_base_class(self):
        """Test that object base class is skipped."""

        class TestClass:
            attr: str

        # Should not include anything from object
        hints = get_all_type_hints(TestClass)
        assert hints == {"attr": str}


class TestNeedsImplementation:
    """Disjunct tests for needs_implementation function - targeting missing coverage."""

    def test_annotation_without_implementation(self):
        """Test annotation exists but no implementation."""

        class TestClass:
            attr: str  # Annotated but not implemented

        assert needs_implementation(TestClass, "attr")

    def test_annotation_with_implementation(self):
        """Test annotation exists with implementation."""

        class TestClass:
            attr: str = "implemented"

        assert not needs_implementation(TestClass, "attr")

    def test_no_annotation_no_implementation(self):
        """Test neither annotation nor implementation exists."""

        class TestClass:
            pass

        assert not needs_implementation(TestClass, "nonexistent")

    def test_abstract_method_needs_implementation(self):
        """Test abstract method detection - TARGET LINE 135."""

        class AbstractClass(ABC):
            @abstractmethod
            def abstract_method(self) -> None:
                pass

        # This should hit line 135: return True for abstract method
        assert needs_implementation(AbstractClass, "abstract_method")

    def test_cached_property_with_abstract_method(self):
        """Test cached_property with abstract underlying function - TARGET LINE 143."""

        class AbstractClass(ABC):
            @cached_property
            @abstractmethod
            def abstract_cached_prop(self) -> str:
                pass

        # This should hit line 143: return True for abstract cached_property
        assert needs_implementation(AbstractClass, "abstract_cached_prop")

    def test_regular_cached_property_not_abstract(self):
        """Test regular cached_property is not considered needing implementation."""

        class RegularClass:
            @cached_property
            def regular_cached_prop(self) -> str:
                return "implemented"

        assert not needs_implementation(RegularClass, "regular_cached_prop")

    def test_inheritance_hierarchy_abstract_search(self):
        """Test abstract method detection in inheritance hierarchy."""

        class Base(ABC):
            @abstractmethod
            def base_abstract(self) -> None:
                pass

        class Child(Base):
            pass  # Doesn't implement base_abstract

        assert needs_implementation(Child, "base_abstract")

    def test_non_abstract_method_in_inheritance(self):
        """Test non-abstract method in inheritance hierarchy."""

        class Base:
            def regular_method(self) -> None:
                pass

        class Child(Base):
            pass

        assert not needs_implementation(Child, "regular_method")


class TestCachingStrategy:
    """Test CachingStrategy enum."""

    def test_enum_values(self):
        """Test enum has correct values."""
        from src.reactor_di.caching import CachingStrategy

        assert CachingStrategy.DISABLED.value == "disabled"
        assert CachingStrategy.NOT_THREAD_SAFE.value == "not_thread_safe"
