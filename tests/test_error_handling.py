"""Test cases providing evidence for the need of some try/except blocks in the main code."""

import pytest
from typing import Any, List, Dict, Union

from reactor_di.type_utils import (
    get_all_type_hints,
    safe_get_type_hints,
    has_constructor_assignment,
    can_resolve_attribute,
    is_type_compatible,
)
from reactor_di.module import module
from reactor_di.law_of_demeter import law_of_demeter


class TestGetTypeHintsErrorHandling:
    """Test error handling in type hint functions."""

    def test_get_all_type_hints_with_forward_reference_to_undefined_class(self):
        """Test that get_all_type_hints handles forward references to undefined classes."""

        class WithForwardRef:
            attr: "UndefinedClass"

        # Should not crash, should return empty dict or handle gracefully
        hints = get_all_type_hints(WithForwardRef)
        assert isinstance(hints, dict)  # Should not crash

    def test_get_all_type_hints_with_invalid_type_syntax(self):
        """Test that get_all_type_hints handles invalid type syntax."""
        # Create class with invalid annotations
        BadClass = type("BadClass", (), {"__annotations__": {"attr": "List["}})

        # Should not crash
        hints = get_all_type_hints(BadClass)
        assert isinstance(hints, dict)  # Should not crash

    def test_get_all_type_hints_with_missing_module_import(self):
        """Test that get_all_type_hints handles missing module imports."""

        class MissingImport:
            attr: "nonexistent_module.SomeClass"

        # Should not crash
        hints = get_all_type_hints(MissingImport)
        assert isinstance(hints, dict)  # Should not crash

    def test_safe_get_type_hints_fallback_behavior(self):
        """Test that safe_get_type_hints provides fallback behavior."""

        # Test with problematic class
        class ProblematicClass:
            attr: "UndefinedClass"

        # Should fallback to raw annotations
        hints = safe_get_type_hints(ProblematicClass)
        assert isinstance(hints, dict)
        # Should have the raw annotation string
        assert "attr" in hints or len(hints) == 0  # Allow empty fallback


class TestInspectGetSourceErrorHandling:
    """Test error handling in inspect.getsource usage."""

    def test_has_constructor_assignment_with_builtin_int(self):
        """Test that has_constructor_assignment handles built-in int class."""
        # Should not crash, should return False
        result = has_constructor_assignment(int, "real")
        assert result is False

    def test_has_constructor_assignment_with_builtin_str(self):
        """Test that has_constructor_assignment handles built-in str class."""
        # Should not crash, should return False
        result = has_constructor_assignment(str, "value")
        assert result is False

    def test_has_constructor_assignment_with_datetime(self):
        """Test that has_constructor_assignment handles datetime class."""
        import datetime

        # Should not crash, should return False
        result = has_constructor_assignment(datetime.datetime, "year")
        assert result is False

    def test_has_constructor_assignment_with_class_without_init(self):
        """Test that has_constructor_assignment handles class without __init__."""

        class NoInit:
            pass

        # Should not crash, should return False
        result = has_constructor_assignment(NoInit, "attr")
        assert result is False

    def test_has_constructor_assignment_with_dynamically_created_class(self):
        """Test that has_constructor_assignment handles dynamically created classes."""

        def dynamic_init(self, attr):
            self.attr = attr

        DynamicClass = type("DynamicClass", (), {"__init__": dynamic_init})

        # Should not crash, should return reasonable result
        result = has_constructor_assignment(DynamicClass, "attr")
        assert isinstance(result, bool)  # Should not crash


class TestTypeCompatibilityErrorHandling:
    """Test error handling in type compatibility checking."""

    def test_is_type_compatible_with_complex_generics(self):
        """Test that is_type_compatible handles complex generic types."""
        # Should not crash with complex generic types
        result = is_type_compatible(List, List[int])
        assert isinstance(result, bool)

    def test_is_type_compatible_with_union_types(self):
        """Test that is_type_compatible handles Union types."""
        # Should not crash with Union types
        result = is_type_compatible(Union[int, str], int)
        assert isinstance(result, bool)


class TestCanResolveAttributeErrorHandling:
    """Test error handling in can_resolve_attribute."""

    def test_can_resolve_attribute_with_problematic_base_type(self):
        """Test that can_resolve_attribute handles problematic base types."""

        class ProblematicClass:
            base: "UndefinedClass"

        # Should not crash
        result = can_resolve_attribute(ProblematicClass, "base", "some_attr")
        assert isinstance(result, bool)

    def test_can_resolve_attribute_with_missing_class(self):
        """Test that can_resolve_attribute handles missing classes."""

        class TestClass:
            pass

        # Should not crash when checking non-existent attributes
        result = can_resolve_attribute(TestClass, "missing", "attr")
        assert isinstance(result, bool)


class TestDecoratorErrorHandling:
    """Test that decorators handle type errors gracefully."""

    def test_module_decorator_with_forward_reference(self):
        """Test that @module decorator handles forward references."""

        # This should not crash during decoration
        @module
        class ModuleWithForwardRef:
            service: "UndefinedService"

        # Should be able to create instance
        instance = ModuleWithForwardRef()
        assert instance is not None

    def test_module_decorator_with_invalid_type(self):
        """Test that @module decorator handles invalid type annotations."""
        # Create class with problematic annotations
        try:

            @module
            class ModuleWithBadType:
                attr: List  # Generic without parameters

            instance = ModuleWithBadType()
            assert instance is not None
        except Exception:
            # If it fails, that's the bug we're testing for
            pytest.fail("@module decorator should handle invalid types gracefully")

    def test_law_of_demeter_decorator_with_problematic_types(self):
        """Test that @law_of_demeter decorator handles problematic types."""

        # This should not crash during decoration
        @law_of_demeter("_internal_attr")
        class LawOfDemeterWithProblematic:
            base: "UndefinedClass"
            _internal_attr: Any
            forwarded_attr: int  # Should be forwarded from _internal_attr

        # Should be able to create instance
        instance = LawOfDemeterWithProblematic()
        assert instance is not None


class TestRealWorldScenarios:
    """Test real-world scenarios that should work."""

    def test_normal_class_with_proper_annotations(self):
        """Test that normal usage still works correctly."""

        class NormalClass:
            def __init__(self, value: int):
                self.value = value

        # Should work fine
        result = has_constructor_assignment(NormalClass, "value")
        assert result is True

    def test_class_with_type_annotation_and_assignment(self):
        """Test class with type annotation and assignment."""

        class TypedClass:
            def __init__(self):
                self.attr: int = 42

        # Should detect the assignment
        result = has_constructor_assignment(TypedClass, "attr")
        assert result is True

    def test_class_with_only_assignment(self):
        """Test class with only assignment (no type annotation)."""

        class AssignmentClass:
            def __init__(self):
                self.attr = "value"

        # Should detect the assignment
        result = has_constructor_assignment(AssignmentClass, "attr")
        assert result is True

    def test_class_without_target_attribute(self):
        """Test class that doesn't have the target attribute."""

        class NoTargetClass:
            def __init__(self):
                self.other_attr = "value"

        # Should return False for non-existent attribute
        result = has_constructor_assignment(NoTargetClass, "missing_attr")
        assert result is False
