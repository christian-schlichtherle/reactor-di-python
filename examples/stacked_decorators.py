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
        self.api = API()
        self.config = Config()
        self.namespace = "production"


@law_of_demeter("_config")  # Sets up: self._timeout = self._config.timeout etc
@law_of_demeter("_api")  # Sets up: self._name = self._api.name etc
@law_of_demeter("_module")  # Sets up: self._api = self._module.api etc
class ResourceController:
    """Resource controller with multiple decorator integration."""

    # From _module
    _api: API
    _config: Config
    _namespace: str

    # From _api
    _name: str

    # From _config
    _is_dry_run: bool
    _timeout: int

    def __init__(self, module: AppModule):
        self._module = module


def test_stacked_decorator_forwarding():
    """Test that all properties are properly set up by the stacked decorators."""
    module = AppModule()
    controller = ResourceController(module)

    # Constructor
    assert controller._module is module

    # From _module
    assert controller._api is module.api
    assert controller._config is module.config
    assert controller._namespace == "production"

    # From _api
    assert controller._name == "TestAPI"

    # From _config
    assert not controller._is_dry_run
    assert controller._timeout == 30


def test_changes():
    """Test that all properties respect changes to their base properties."""
    module = AppModule()
    controller = ResourceController(module)

    # Change module
    module.api = API()
    module.config = Config()

    # Constructor
    assert controller._module is module

    # From _module
    assert controller._api is module.api
    assert controller._config is module.config
    assert controller._namespace == "production"

    # From _api
    assert controller._name == "TestAPI"

    # From _config
    assert not controller._is_dry_run
    assert controller._timeout == 30
