"""Tests for pure_hasattr function in type_utils module."""

from reactor_di.type_utils import pure_hasattr


class TestPureHasattr:
    """Test pure_hasattr function that checks attributes without side effects."""

    def test_instance_dict_attribute(self):
        """Test detection of attributes in instance __dict__."""

        class SimpleClass:
            def __init__(self):
                self.instance_attr = 42

        obj = SimpleClass()
        assert pure_hasattr(obj, "instance_attr") is True
        assert pure_hasattr(obj, "missing_attr") is False

    def test_class_dict_attribute(self):
        """Test detection of attributes in class __dict__."""

        class ClassWithClassAttr:
            class_attr = "class_value"

            def method(self):
                pass

        obj = ClassWithClassAttr()
        assert pure_hasattr(obj, "class_attr") is True
        assert pure_hasattr(obj, "method") is True
        assert pure_hasattr(obj, "missing") is False

    def test_inherited_attributes(self):
        """Test detection of attributes from parent classes via __mro__."""

        class Parent:
            parent_attr = "from_parent"

            def parent_method(self):
                pass

        class Child(Parent):
            child_attr = "from_child"

        obj = Child()
        assert pure_hasattr(obj, "child_attr") is True
        assert pure_hasattr(obj, "parent_attr") is True
        assert pure_hasattr(obj, "parent_method") is True
        assert pure_hasattr(obj, "missing") is False

    def test_slots_attributes(self):
        """Test detection of attributes defined in __slots__."""

        class SlottedClass:
            __slots__ = ["slot_attr", "another_slot"]

            def __init__(self):
                self.slot_attr = "slot_value"

        obj = SlottedClass()
        assert pure_hasattr(obj, "slot_attr") is True
        assert pure_hasattr(obj, "another_slot") is True  # Even if not set
        assert pure_hasattr(obj, "missing") is False

    def test_mixed_slots_and_dict(self):
        """Test classes with both __slots__ and __dict__."""

        class MixedClass:
            __slots__ = ["slot_attr"]

            def __init__(self):
                self.slot_attr = "slot"

        class ChildWithDict(MixedClass):
            # Child doesn't define __slots__, so gets __dict__
            def __init__(self):
                super().__init__()
                self.dict_attr = "dict"

        obj = ChildWithDict()
        assert pure_hasattr(obj, "slot_attr") is True
        assert pure_hasattr(obj, "dict_attr") is True
        assert pure_hasattr(obj, "missing") is False

    def test_property_not_triggered(self):
        """Test that properties are detected but not executed."""

        class ClassWithProperty:
            _counter = 0

            @property
            def expensive_property(self):
                # This should NOT be called during pure_hasattr
                ClassWithProperty._counter += 1
                return "expensive_result"

        obj = ClassWithProperty()
        initial_count = ClassWithProperty._counter

        # Check property exists without triggering it
        assert pure_hasattr(obj, "expensive_property") is True
        assert ClassWithProperty._counter == initial_count  # Not incremented

        # Verify property still works normally
        _ = obj.expensive_property
        assert ClassWithProperty._counter == initial_count + 1

    def test_descriptor_not_triggered(self):
        """Test that descriptors are detected but not executed."""

        class Descriptor:
            accessed = False

            def __get__(self, obj, objtype=None):
                Descriptor.accessed = True
                return "descriptor_value"

            def __set__(self, obj, value):
                pass

        class ClassWithDescriptor:
            desc_attr = Descriptor()

        obj = ClassWithDescriptor()
        Descriptor.accessed = False

        # Check descriptor exists without triggering it
        assert pure_hasattr(obj, "desc_attr") is True
        assert Descriptor.accessed is False  # Not triggered

        # Verify descriptor still works normally
        _ = obj.desc_attr
        assert Descriptor.accessed is True

    def test_no_dict_or_slots(self):
        """Test objects without __dict__ or __slots__ (like built-ins)."""
        # Integer objects don't have __dict__
        num = 42
        assert pure_hasattr(num, "real") is True  # int has 'real' attribute
        assert pure_hasattr(num, "bit_length") is True  # int method
        assert pure_hasattr(num, "missing") is False

    def test_attribute_error_handling(self):
        """Test handling of objects that raise AttributeError for __dict__ access."""

        class NoDict:
            # Explicitly prevent __dict__ access
            @property
            def __dict__(self):
                raise AttributeError("No __dict__ for you!")

            class_attr = "value"

        obj = NoDict()
        # Should still detect class attributes even if __dict__ raises
        assert pure_hasattr(obj, "class_attr") is True
        assert pure_hasattr(obj, "missing") is False

    def test_multiple_inheritance(self):
        """Test detection through complex multiple inheritance."""

        class A:
            attr_a = "a"

        class B:
            attr_b = "b"

        class C(A, B):
            attr_c = "c"

        obj = C()
        assert pure_hasattr(obj, "attr_a") is True
        assert pure_hasattr(obj, "attr_b") is True
        assert pure_hasattr(obj, "attr_c") is True
        assert pure_hasattr(obj, "missing") is False

    def test_dynamic_attributes(self):
        """Test detection of dynamically added attributes."""

        class DynamicClass:
            pass

        obj = DynamicClass()
        assert pure_hasattr(obj, "dynamic") is False

        # Add attribute dynamically
        obj.dynamic = "added"
        assert pure_hasattr(obj, "dynamic") is True

        # Add class attribute dynamically
        DynamicClass.class_dynamic = "class_added"
        assert pure_hasattr(obj, "class_dynamic") is True

    def test_special_attributes(self):
        """Test detection of special/magic attributes."""

        class SpecialClass:
            def __init__(self):
                self.regular = "normal"

            def __str__(self):
                return "special"

        obj = SpecialClass()
        assert pure_hasattr(obj, "__str__") is True
        assert pure_hasattr(obj, "__class__") is True
        assert pure_hasattr(obj, "__dict__") is True
        assert pure_hasattr(obj, "regular") is True

    def test_empty_class(self):
        """Test behavior with completely empty class."""

        class Empty:
            pass

        obj = Empty()
        assert pure_hasattr(obj, "__class__") is True  # Always has __class__
        assert pure_hasattr(obj, "missing") is False

    def test_slots_with_inheritance(self):
        """Test __slots__ inheritance scenarios."""

        class Parent:
            __slots__ = ["parent_slot"]

        class Child(Parent):
            __slots__ = ["child_slot"]

        obj = Child()
        assert pure_hasattr(obj, "parent_slot") is True
        assert pure_hasattr(obj, "child_slot") is True
        assert pure_hasattr(obj, "missing") is False

    def test_cached_property_not_triggered(self):
        """Test that cached_property is detected but not executed."""
        from functools import cached_property

        class ClassWithCachedProperty:
            _call_count = 0

            @cached_property
            def expensive_cached(self):
                ClassWithCachedProperty._call_count += 1
                return "cached_result"

        obj = ClassWithCachedProperty()
        initial_count = ClassWithCachedProperty._call_count

        # Check cached_property exists without triggering it
        assert pure_hasattr(obj, "expensive_cached") is True
        assert ClassWithCachedProperty._call_count == initial_count  # Not called

        # Verify cached_property still works
        result = obj.expensive_cached
        assert ClassWithCachedProperty._call_count == initial_count + 1
        assert result == "cached_result"
