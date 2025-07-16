# Product Requirements Document (PRD)
## Reactor DI Python - Code Redesign

### Executive Summary

This PRD outlines the comprehensive redesign of the Reactor DI Python codebase to ensure all examples work correctly, achieve 100% test coverage, and implement robust attribute detection mechanisms for both `@law_of_demeter` and `@module` decorators.

### Current State Analysis

#### Implementation Status
- **Complete Code Removal**: All implementation has been replaced with stubs (`...`)
- **Test Suite Removal**: All tests have been removed from `tests/` directory (only `__init__.py` remains)
- **Examples Status**: All examples fail to run due to stubbed decorators (`TypeError: 'NoneType' object is not callable`)

#### Files Status
- `src/reactor_di/__init__.py` - ✅ Import structure intact
- `src/reactor_di/caching.py` - ✅ Full implementation and docstrings intact
- `src/reactor_di/law_of_demeter.py` - ❌ Stubbed implementation (`...`)
- `src/reactor_di/module.py` - ❌ Stubbed implementation (`...`)
- `src/reactor_di/type_utils.py` - ❌ Stubbed implementation (`...`)
- `tests/` directory - ❌ All test files removed

#### Documentation Status
- `README.md` - ❌ Contains outdated information about examples, features, and API
- `CLAUDE.md` - ❌ Contains outdated architectural information and development commands
- All docstrings in stubbed files - ❌ Completely removed

#### Example Improvements (Recent Commits)
- **`examples/caching_strategy.py`**: Simplified `MyService` → `ServiceMock` with clean `pass` implementation
- **`examples/custom_prefix.py`**: Alphabetically sorted annotations for better readability
- **`examples/quick_start.py`**: Clean test structure with proper spacing
- **`examples/quick_start_advanced.py`**: Clean test structure with proper spacing
- **`examples/side_effects.py`**: Updated to use `@law_of_demeter("pool")` with `connections: int` forwarding
- **`examples/stacked_decorators.py`**: Renamed `test_changes()` → `test_respect_changes()` for clarity

### Problem Statement

The current codebase has been completely stubbed out, requiring a full reimplementation from scratch:

1. **Complete Implementation Gap**: Both `@law_of_demeter` and `@module` decorators are stubbed (`...`) and non-functional.

2. **Missing Core Infrastructure**: The `type_utils.py` file has been removed, eliminating all shared type checking utilities.

3. **No Test Coverage**: All tests have been removed from the `tests/` directory, leaving no validation framework.

4. **Outdated Documentation**: All documentation files contain information about features and APIs that no longer exist.

5. **Missing Docstrings**: All function and class docstrings have been removed with the stubbed implementation.

### Design Objectives

#### 1. Make Examples Work (Non-Negotiable Specification)
All code in the `examples/` folder must work as-is. The examples serve as the definitive specification and cannot be changed unless proven wrong.

#### 2. Achieve 100% Test Coverage
Update test suite to ensure comprehensive coverage of all code paths in `src/reactor_di/`.

#### 3. Implement Robust Attribute Detection
Develop a multi-layered attribute detection system that can handle:
- Class-level annotations
- Constructor-created attributes
- Dynamic attributes
- Abstract methods/properties
- Inherited attributes

#### 4. Decorator Behaviour Specification
- **`@law_of_demeter` (Reluctant)**: Silently skip attributes that cannot be proven to exist
- **`@module` (Greedy)**: Raise errors for attributes that cannot be satisfied

### Technical Requirements

#### 1. Enhanced Attribute Detection System

**Multi-Layer Detection Strategy:**
```python
def can_resolve_attribute(cls, base_ref, target_attr_name):
    """Multi-layer attribute detection strategy."""
    # Layer 1: Static analysis (annotations, class attributes)
    if has_static_evidence(cls, base_ref, target_attr_name):
        return True
    
    # Layer 2: Constructor analysis (AST parsing, not execution)
    if has_constructor_evidence(cls, base_ref, target_attr_name):
        return True
    
    # Layer 3: Runtime deferred resolution (for @law_of_demeter only)
    if supports_deferred_resolution(cls, base_ref, target_attr_name):
        return True
    
    return False
```

**Key Features:**
- No source code scanning (per requirements)
- No constructor parameter analysis (per requirements)
- Support for deferred runtime resolution with side-effect protection
- Comprehensive type compatibility validation

#### 2. Deferred Runtime Resolution

For attributes that cannot be statically proven to exist (like `Config` attributes created in constructor), implement deferred resolution:

```python
class DeferredProperty:
    """Property that resolves target existence at first access."""
    
    def __init__(self, base_ref, target_attr_name, expected_type):
        self.base_ref = base_ref
        self.target_attr_name = target_attr_name
        self.expected_type = expected_type
        self._resolved_property = None
    
    def __get__(self, instance, owner):
        if instance is None:
            return self
        
        if self._resolved_property is None:
            # Resolve at first access
            base_obj = getattr(instance, self.base_ref)
            if not hasattr(base_obj, self.target_attr_name):
                raise AttributeError(f"Runtime resolution failed: {self.base_ref}.{self.target_attr_name} not found")
            
            # Validate type compatibility if possible
            if self.expected_type is not None:
                self._validate_runtime_type_compatibility(base_obj, self.target_attr_name, self.expected_type)
            
            # Create resolved property
            self._resolved_property = self._create_forwarding_property()
        
        return self._resolved_property.__get__(instance, owner)
```

#### 3. Side Effect Protection

Implement safeguards to prevent side effects during attribute detection:

```python
def safe_attribute_probe(target_type, attr_name):
    """Safely probe for attribute existence without side effects."""
    # Check annotations first
    if attr_name in get_all_type_hints(target_type):
        return True
    
    # Check class attributes
    if hasattr(target_type, attr_name):
        return True
    
    # For dynamic attributes, use deferred resolution
    # Never instantiate objects during decoration time
    return False
```

#### 4. Decorator Behavior Implementation

**`@law_of_demeter` (Reluctant Behavior):**
```python
def law_of_demeter_decorator(cls):
    for attr_name, attr_type in annotations.items():
        if can_resolve_attribute(cls, base_ref, target_attr_name):
            # Create property (static or deferred)
            create_property(cls, attr_name, attr_type)
        else:
            # Silently skip - let other decorators handle it
            continue
```

**`@module` (Greedy Behavior):**
```python
def module_decorator(cls):
    for attr_name, attr_type in annotations.items():
        if not can_resolve_attribute(cls, attr_name, attr_type):
            raise TypeError(f"Unsatisfied dependency: {attr_name}: {attr_type}")
        # Create factory method
        create_factory_method(cls, attr_name, attr_type)
```

### Implementation Plan

#### Phase 1: Core Infrastructure Reconstruction (High Priority)

1. **Recreate Type Utilities (`type_utils.py`)**
   - Implement `get_all_type_hints()` for MRO traversal
   - Create `safe_get_type_hints()` with fallback handling
   - Implement `needs_implementation()` for attribute analysis
   - Add `is_type_compatible()` for type validation
   - Create comprehensive docstrings for all functions
   - **Note**: `type_utils.py` file exists but is completely stubbed out

2. **Deferred Resolution System**
   - Create `DeferredProperty` class for runtime resolution
   - Implement side-effect protection mechanisms
   - Add runtime type validation
   - Document the deferred resolution architecture

3. **Decorator Implementation**
   - Implement `@law_of_demeter` with reluctant behavior
   - Implement `@module` with greedy behavior
   - Ensure seamless cooperation between decorators
   - Add comprehensive docstrings for all decorators

#### Phase 2: Make Examples Work (High Priority)

1. **Implementation Validation**
   - Ensure all examples pass without modification
   - Focus on the failing `examples/side_effects.py` case
   - Test all caching strategies and prefix variations
   - Validate stacked decorator scenarios

2. **Example Coverage**
   - Verify `examples/caching_strategy.py` works correctly with `ServiceMock` class
   - Test `examples/custom_prefix.py` prefix variations (alphabetically sorted annotations)
   - Validate `examples/quick_start.py` basic functionality (clean test structure)
   - Ensure `examples/quick_start_advanced.py` inheritance works (clean test structure)
   - Fix `examples/side_effects.py` connection forwarding with `pool` reference
   - Test `examples/stacked_decorators.py` multi-decorator scenarios (renamed `test_respect_changes`)

3. **CI Pipeline Compliance**
   - **Code must pass `ruff check src tests examples`** (linting)
   - **Code must pass `black --check src tests examples`** (formatting)
   - **Code must pass `mypy src`** (type checking)
   - **Code must pass `pytest`** (tests)
   - **Matrix testing across Python 3.8-3.13**
   - All CI pipeline steps must succeed for deployment

#### Phase 3: Test Suite Creation (High Priority)

1. **Comprehensive Test Coverage**
   - Create `tests/test_type_utils.py` with **100% line and branch coverage**
   - Create `tests/test_law_of_demeter.py` with **100% line and branch coverage**
   - Create `tests/test_module.py` with **100% line and branch coverage**
   - Create `tests/test_caching.py` with **100% line and branch coverage**
   - Create `tests/test_integration.py` for decorator cooperation
   - **Achieve 100% test coverage on ALL files in `src/` folder** (non-negotiable)

2. **Testing Infrastructure**
   - Implement realistic test scenarios (not mocked edge cases)
   - Focus on meaningful assertions over coverage metrics
   - Test complex inheritance hierarchies
   - Validate error conditions and edge cases
   - **Every line, branch, and code path must be tested**

#### Phase 4: Documentation Reconstruction (High Priority)

1. **Code Documentation**
   - Write comprehensive docstrings for all functions and classes
   - Document decorator behavior with examples
   - Explain deferred resolution mechanism
   - Document type compatibility validation
   - Add usage examples in docstrings

2. **Project Documentation**
   - **Update `README.md`**:
     - Fix outdated API references
     - Update examples to match working implementation
     - Document new features and limitations
     - Update development commands and testing instructions
   - **Update `CLAUDE.md`**:
     - Document new architectural patterns
     - Update development workflow
     - Fix testing commands and coverage requirements
     - Document the reluctant vs greedy behavior
   - **Create comprehensive docstrings** for all public APIs

### Success Criteria

#### Must-Have (Release Blockers)
1. ✅ All examples in `examples/` folder pass tests without modification
2. ✅ **100% test coverage on ALL code in `src/` folder** (non-negotiable requirement)
3. ✅ `@law_of_demeter` properly implements reluctant behavior
4. ✅ `@module` properly implements greedy behavior
5. ✅ No side effects during decoration time
6. ✅ Robust type compatibility validation
7. ✅ **Comprehensive docstrings** for all public functions and classes
8. ✅ **Updated `README.md`** with correct API documentation
9. ✅ **Updated `CLAUDE.md`** with current architectural information
10. ✅ **CI Pipeline Compliance**: Code must pass all CI checks:
    - `ruff check src tests examples` (linting)
    - `black --check src tests examples` (formatting)
    - `mypy src` (type checking)
    - `pytest` (tests)
    - Matrix testing across Python 3.8-3.13

#### Should-Have (Quality Metrics)
1. ✅ Clean, maintainable code architecture
2. ✅ Proper error messages for debugging
3. ✅ Performance optimization for common cases
4. ✅ **Detailed examples in docstrings** for all public APIs
5. ✅ **Accurate documentation** of all decorator parameters and behavior

#### Nice-to-Have (Future Enhancements)
1. ⭐ Enhanced IDE support and type hints
2. ⭐ Performance benchmarks and optimization
3. ⭐ Additional caching strategies
4. ⭐ Plugin system for custom attribute resolution

### Risk Assessment

#### High Risk
- **Runtime Resolution Complexity**: Deferred resolution adds complexity but is necessary for constructor-created attributes
- **Side Effect Prevention**: Must ensure no unintended side effects during attribute probing

#### Medium Risk
- **Performance Impact**: Runtime resolution may impact performance, but should be minimal with proper caching
- **Type Validation Edge Cases**: Complex type hierarchies may require additional validation logic

#### Low Risk
- **Backward Compatibility**: Changes should be mostly internal with minimal API changes
- **Documentation Maintenance**: Standard documentation update process

### Testing Strategy

#### Unit Tests
- **`tests/test_type_utils.py`**: Test all type utility functions with **100% coverage**
- **`tests/test_law_of_demeter.py`**: Test `@law_of_demeter` decorator with **100% coverage**
- **`tests/test_module.py`**: Test `@module` decorator with **100% coverage**
- **`tests/test_caching.py`**: Test caching strategies with **100% coverage**
- Test deferred resolution mechanism with **100% coverage**
- Test error conditions and edge cases with **100% coverage**
- **Every single line of code in `src/` must be executed by tests**

#### Integration Tests
- **`tests/test_integration.py`**: Test decorator cooperation scenarios
- Test complex inheritance hierarchies
- Test all example scenarios as integration tests
- Validate seamless cooperation between `@law_of_demeter` and `@module`

#### Example Tests
- All `examples/*.py` files serve as integration tests
- Must pass without modification (specification compliance)
- Test real-world usage patterns

#### Documentation Tests
- Validate all docstring examples work correctly
- Test API documentation accuracy
- Ensure README examples match implementation

### Conclusion

This redesign involves a complete reconstruction of the Reactor DI codebase from stubbed implementations to a fully functional dependency injection system. The implementation prioritizes correctness and reliability over performance, ensuring all examples work as specified while achieving comprehensive test coverage.

**Key Deliverables:**
- Complete reimplementation of `@law_of_demeter` and `@module` decorators
- Recreation of the `type_utils.py` module with comprehensive type checking
- **Full test suite creation with 100% coverage on ALL `src/` code** (non-negotiable)
- **Comprehensive docstring recreation** for all public APIs
- **Complete documentation updates** for `README.md` and `CLAUDE.md`
- Validation that all examples work without modification
- **Every single line of code in `src/` folder must be tested**
- **CI Pipeline Compliance**: All code must pass ruff, black, mypy, and pytest checks

The reluctant vs greedy behavior distinction provides clear semantics for decorator cooperation, while the deferred resolution system handles edge cases that cannot be statically analyzed. The extensive documentation requirements ensure that the codebase is maintainable and accessible to developers.

The result will be a production-ready dependency injection system that works reliably across diverse Python codebases, with comprehensive documentation that accurately reflects the implementation.