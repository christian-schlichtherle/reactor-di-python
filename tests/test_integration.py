"""Integration tests for decorator cooperation and cross-module functionality."""

# type: ignore

from abc import ABC

import pytest

from src.reactor_di.caching import CachingStrategy
from src.reactor_di.law_of_demeter import law_of_demeter
from src.reactor_di.module import module


class TestDecoratorIntegration:
    """Test integration between @module and @law_of_demeter decorators."""

    def test_validation_skips_implemented_dependencies(self):
        """Test that validation only checks unimplemented dependencies."""

        class MockConfig:
            available_attr = "test_value"
            # Note: missing_attr is not available

        # This class has law_of_demeter applied first
        @law_of_demeter("_config")
        class MockComponent(ABC):
            _available_attr: str  # Should be implemented by law_of_demeter
            _missing_attr: str  # Should NOT be implemented by law_of_demeter
            _config: (
                MockConfig  # Should NOT be implemented by law_of_demeter (base ref)
            )

        # Check that law_of_demeter only implemented the available attribute
        assert hasattr(
            MockComponent, "_available_attr"
        ), "law_of_demeter should implement _available_attr"
        # Verify behavioral functionality of implemented attribute
        assert isinstance(MockComponent._available_attr, property)
        test_instance = MockComponent()
        test_instance._config = MockConfig()
        assert test_instance._available_attr == "test_value"

        assert not hasattr(
            MockComponent, "_missing_attr"
        ), "law_of_demeter should NOT implement _missing_attr"
        # Verify missing attribute truly doesn't exist and would fail
        with pytest.raises(AttributeError):
            _ = test_instance._missing_attr

        assert not hasattr(
            MockComponent, "_config"
        ), "law_of_demeter should NOT implement _config (base ref)"
        # Verify base ref is handled manually, not by decorator
        assert test_instance._config.available_attr == "test_value"

        # Now module decorator should only validate unimplemented dependencies
        @module(CachingStrategy.NOT_THREAD_SAFE)
        class MockModule:
            component: MockComponent

            @property
            def config(self):
                return MockConfig()

            @property
            def missing_attr(self):
                return "provided_by_module"

        # This should work - validation should only check _config and _missing_attr
        module_instance = MockModule()
        component = module_instance.component

        # Test the full dependency chain
        # Note: Property access may create new instances, so we check by value
        assert isinstance(component._config, MockConfig)
        assert component._available_attr == "test_value"
        assert component._missing_attr == "provided_by_module"

    def test_selective_property_creation(self):
        """Test that law_of_demeter selectively creates properties."""

        class MockBase:
            existing_prop = "exists"
            # missing_prop does not exist

        @law_of_demeter("_base")
        class TestClass:
            _existing_prop: str  # Should be created (MockBase has this)
            _missing_prop: str  # Should NOT be created (MockBase doesn't have this)
            _base: MockBase  # Should NOT be created (base reference itself)

        # Test actual property creation
        assert hasattr(
            TestClass, "_existing_prop"
        ), "Should create property for existing attribute"
        # Verify behavioral functionality of created property
        assert isinstance(TestClass._existing_prop, property)
        test_instance = TestClass()
        test_instance._base = MockBase()
        assert test_instance._existing_prop == "exists"

        assert not hasattr(
            TestClass, "_missing_prop"
        ), "Should NOT create property for missing attribute"
        # Verify missing property access fails appropriately
        with pytest.raises(AttributeError):
            _ = test_instance._missing_prop

        assert not hasattr(
            TestClass, "_base"
        ), "Should NOT create property for base reference"
        # Verify base reference works as normal attribute
        assert test_instance._base.existing_prop == "exists"

    def test_law_of_demeter_with_pydantic_models(self):
        """Test law_of_demeter works with Pydantic-style models."""

        # Mock a Pydantic-style model
        class MockPydanticConfig:
            def __init__(self):
                self.field1 = "value1"
                self.field2 = "value2"

            # Pydantic models have annotations
            __annotations__ = {
                "field1": str,
                "field2": str,
            }

        @law_of_demeter("_config")
        class TestComponent:
            _field1: str  # Should be created (in annotations)
            _field2: str  # Should be created (in annotations)
            _nonexistent: str  # Should NOT be created (not in annotations)
            _config: MockPydanticConfig

        assert hasattr(TestComponent, "_field1")
        # Verify property type and behavior for field1
        assert isinstance(TestComponent._field1, property)

        assert hasattr(TestComponent, "_field2")
        # Verify property type and behavior for field2
        assert isinstance(TestComponent._field2, property)

        assert not hasattr(TestComponent, "_nonexistent")
        # Verify nonexistent field access fails at instance level
        temp_instance = TestComponent()
        temp_instance._config = MockPydanticConfig()
        with pytest.raises(AttributeError):
            _ = temp_instance._nonexistent

        # Test runtime behavior
        instance = TestComponent()
        instance._config = MockPydanticConfig()

        assert instance._field1 == "value1"
        assert instance._field2 == "value2"

    def test_module_synthesis_with_partial_implementation(self):
        """Test module synthesis when component has partial implementation."""

        class MockConfig:
            app_name = "test-app"
            # No namespace attribute

        @law_of_demeter("_config")
        class PartiallyImplementedComponent(ABC):
            _app_name: str  # Implemented by law_of_demeter
            _namespace: str  # Not implemented by law_of_demeter
            _config: MockConfig  # Not implemented by law_of_demeter (base ref)

        # Verify partial implementation
        assert hasattr(PartiallyImplementedComponent, "_app_name")
        # Verify _app_name property is properly implemented
        assert isinstance(PartiallyImplementedComponent._app_name, property)

        assert not hasattr(PartiallyImplementedComponent, "_namespace")
        # Verify _namespace is truly missing from class
        assert "_namespace" not in PartiallyImplementedComponent.__dict__

        assert not hasattr(PartiallyImplementedComponent, "_config")
        # Verify _config is not implemented as property by decorator
        assert "_config" not in PartiallyImplementedComponent.__dict__

        @module(CachingStrategy.NOT_THREAD_SAFE)
        class TestModule:
            component: PartiallyImplementedComponent

            @property
            def config(self):
                return MockConfig()

            @property
            def namespace(self):
                return "test-namespace"

        # Test full synthesis
        module_instance = TestModule()
        component = module_instance.component

        assert (
            component._app_name == "test-app"
        )  # From law_of_demeter -> config.app_name
        assert (
            component._namespace == "test-namespace"
        )  # From module -> module.namespace
        assert isinstance(component._config, MockConfig)  # From module -> module.config

    def test_error_handling_with_cooperation(self):
        """Test error handling when decorators cooperate incorrectly."""

        class MockConfig:
            # This config doesn't have the required attribute
            pass

        @law_of_demeter("_config")
        class ComponentWithMissingDeps(ABC):
            _missing_in_config: str  # Config doesn't have this
            _missing_in_module: str  # Module won't provide this either
            _config: MockConfig

        # law_of_demeter should not implement _missing_in_config
        assert not hasattr(ComponentWithMissingDeps, "_missing_in_config")
        # Verify property is truly not created in class dict
        assert "_missing_in_config" not in ComponentWithMissingDeps.__dict__
        # Verify instance access would fail without module providing it
        temp_instance = ComponentWithMissingDeps()
        temp_instance._config = MockConfig()
        with pytest.raises(AttributeError):
            _ = temp_instance._missing_in_config

        # Module should fail validation for missing dependencies
        # The validation will check both _missing_in_config and _missing_in_module
        # since neither was implemented by law_of_demeter
        with pytest.raises(TypeError, match="requires dependency '_missing_in_config"):

            @module(CachingStrategy.DISABLED)
            class BadModule:
                component: ComponentWithMissingDeps

                @property
                def config(self):
                    return MockConfig()

                # Missing: missing_in_config AND missing_in_module properties
