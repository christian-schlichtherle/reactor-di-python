"""Multiple decorators example for reactor-di.

This example demonstrates using multiple @law_of_demeter decorators on the same class:
- First decorator forwards properties from _config
- Second decorator forwards properties from _module
- Shows auto-setup behavior where self._config = self._module.config
"""

from reactor_di import law_of_demeter


class Config:
    """Configuration class with various settings."""

    def __init__(self):
        self.timeout = 30
        self.is_dry_run = False


class API:
    """API service class."""

    def __init__(self):
        self.name = "TestAPI"


class AppModule:
    """Application module containing config and services."""

    def __init__(self):
        self.config = Config()
        self.api = API()
        self.namespace = "production"


@law_of_demeter("_config")  # Creates forwarding properties
@law_of_demeter("_module")  # Auto-setup: self._config = self._module.config
class ResourceController:
    """Resource controller with multiple decorator integration."""

    def __init__(self, module):
        self._module = module
        # Decorator automatically sets up: self._config = module.config

    # From _config
    _timeout: int
    _is_dry_run: bool

    # From _module
    _api: object
    _namespace: str


def test_multiple_decorators_setup():
    """Test that multiple decorators are properly set up."""
    app_module = AppModule()
    controller = ResourceController(app_module)

    # Test that _module is set
    assert controller._module is app_module

    # Test that _config is automatically set from _module.config
    assert controller._config is app_module.config

    # Test that both references point to the same config object
    assert controller._config is controller._module.config


def test_config_property_forwarding():
    """Test that properties are forwarded from _config."""
    app_module = AppModule()
    controller = ResourceController(app_module)

    # Test forwarded properties from _config
    assert controller._timeout == 30
    assert controller._is_dry_run is False

    # Test that changes to config are reflected in forwarded properties
    app_module.config.timeout = 60
    assert controller._timeout == 60

    app_module.config.is_dry_run = True
    assert controller._is_dry_run is True


def test_module_property_forwarding():
    """Test that properties are forwarded from _module."""
    app_module = AppModule()
    controller = ResourceController(app_module)

    # Test forwarded properties from _module
    assert controller._api is app_module.api
    assert controller._namespace == "production"

    # Test that changes to module are reflected in forwarded properties
    new_api = API()
    app_module.api = new_api
    assert controller._api is new_api

    app_module.namespace = "development"
    assert controller._namespace == "development"


def test_auto_setup_behavior():
    """Test the auto-setup behavior where _config = _module.config."""
    app_module = AppModule()
    controller = ResourceController(app_module)

    # The second decorator should automatically set up the _config reference
    # based on the property forwarding from _module
    assert hasattr(controller, "_config")
    assert controller._config is app_module.config

    # Test that the forwarded properties work correctly
    assert controller._timeout == 30
    assert controller._is_dry_run is False

    # Test that changes to the original config are reflected
    app_module.config.timeout = 120
    assert controller._timeout == 120


def test_decorator_order_independence():
    """Test that decorator order doesn't affect functionality."""

    # Create controller with the decorators in the same order as the example
    @law_of_demeter("_config")
    @law_of_demeter("_module")
    class Controller1:
        def __init__(self, module):
            self._module = module

        _timeout: int
        _is_dry_run: bool
        _api: object
        _namespace: str

    # Create controller with decorators in reverse order
    @law_of_demeter("_module")
    @law_of_demeter("_config")
    class Controller2:
        def __init__(self, module):
            self._module = module

        _timeout: int
        _is_dry_run: bool
        _api: object
        _namespace: str

    app_module = AppModule()
    controller1 = Controller1(app_module)
    controller2 = Controller2(app_module)

    # Both should work the same way
    assert controller1._timeout == controller2._timeout
    assert controller1._is_dry_run == controller2._is_dry_run
    assert controller1._api is controller2._api
    assert controller1._namespace == controller2._namespace
