"""Custom prefixes example for reactor-di.

This example demonstrates using custom prefixes with @law_of_demeter decorator:
- No prefix (prefix='') - direct forwarding without prefix
- Custom prefix (prefix='cfg_') - forwarding with custom prefix
- Default prefix (prefix='_') - standard underscore prefix
"""

from reactor_di import law_of_demeter


class Config:
    """Configuration class with various settings."""

    def __init__(self):
        self.timeout = 30
        self.is_dry_run = False
        self.max_retries = 3
        self.debug_mode = True


# No prefix - direct forwarding
@law_of_demeter("config", prefix="")
class DirectController:
    """Controller with direct property forwarding (no prefix)."""

    debug_mode: bool  # → config.debug_mode
    is_dry_run: bool  # → config.is_dry_run
    max_retries: int  # → config.max_retries
    timeout: int  # → config.timeout

    def __init__(self, config: Config):
        self.config = config


# Custom prefix
@law_of_demeter("config", prefix="cfg_")
class PrefixController:
    """Controller with custom prefix for property forwarding."""

    cfg_debug_mode: bool  # → config.debug_mode
    cfg_is_dry_run: bool  # → config.is_dry_run
    cfg_max_retries: int  # → config.max_retries
    cfg_timeout: int  # → config.timeout

    def __init__(self, config: Config):
        self.config = config


# Default prefix (for comparison)
@law_of_demeter("config")  # prefix='_' by default
class DefaultController:
    """Controller with default underscore prefix."""

    _debug_mode: bool  # → config.debug_mode
    _is_dry_run: bool  # → config.is_dry_run
    _max_retries: int  # → config.max_retries
    _timeout: int  # → config.timeout

    def __init__(self, config):
        self.config = config


def test_no_prefix_forwarding():
    """Test direct forwarding without prefix."""

    config = Config()
    controller = DirectController(config)

    # Test direct property access (no prefix)
    assert controller.timeout == 30
    assert controller.is_dry_run is False
    assert controller.max_retries == 3
    assert controller.debug_mode is True

    # Test that changes are reflected
    config.timeout = 60
    assert controller.timeout == 60

    config.is_dry_run = True
    assert controller.is_dry_run is True


def test_custom_prefix_forwarding():
    """Test forwarding with custom prefix."""

    config = Config()
    controller = PrefixController(config)

    # Test custom prefix property access
    assert controller.cfg_timeout == 30
    assert controller.cfg_is_dry_run is False
    assert controller.cfg_max_retries == 3
    assert controller.cfg_debug_mode is True

    # Test that changes are reflected
    config.timeout = 45
    assert controller.cfg_timeout == 45

    config.debug_mode = False
    assert controller.cfg_debug_mode is False


def test_default_prefix_forwarding():
    """Test forwarding with default underscore prefix."""

    config = Config()
    controller = DefaultController(config)

    # Test default prefix property access
    assert controller._timeout == 30
    assert controller._is_dry_run is False
    assert controller._max_retries == 3
    assert controller._debug_mode is True

    # Test that changes are reflected
    config.max_retries = 5
    assert controller._max_retries == 5

    config.is_dry_run = True
    assert controller._is_dry_run is True


def test_prefix_comparison():
    """Test that different prefixes work with the same config."""

    config = Config()

    direct_controller = DirectController(config)
    prefix_controller = PrefixController(config)
    default_controller = DefaultController(config)

    # All should access the same underlying config values
    assert (
        direct_controller.timeout
        == prefix_controller.cfg_timeout
        == default_controller._timeout
    )
    assert (
        direct_controller.is_dry_run
        == prefix_controller.cfg_is_dry_run
        == default_controller._is_dry_run
    )
    assert (
        direct_controller.max_retries
        == prefix_controller.cfg_max_retries
        == default_controller._max_retries
    )
    assert (
        direct_controller.debug_mode
        == prefix_controller.cfg_debug_mode
        == default_controller._debug_mode
    )


def test_dynamic_updates_across_prefixes():
    """Test that dynamic updates work across different prefix styles."""

    config = Config()

    direct_controller = DirectController(config)
    prefix_controller = PrefixController(config)
    default_controller = DefaultController(config)

    # Change config values
    config.timeout = 100
    config.is_dry_run = True
    config.max_retries = 10
    config.debug_mode = False

    # All controllers should reflect the changes
    assert direct_controller.timeout == 100
    assert prefix_controller.cfg_timeout == 100
    assert default_controller._timeout == 100

    assert direct_controller.is_dry_run is True
    assert prefix_controller.cfg_is_dry_run is True
    assert default_controller._is_dry_run is True

    assert direct_controller.max_retries == 10
    assert prefix_controller.cfg_max_retries == 10
    assert default_controller._max_retries == 10

    assert direct_controller.debug_mode is False
    assert prefix_controller.cfg_debug_mode is False
    assert default_controller._debug_mode is False


def test_prefix_attribute_isolation():
    """Test that different prefix styles don't interfere with each other."""

    config = Config()

    # Create controllers with different prefixes
    direct_controller = DirectController(config)
    prefix_controller = PrefixController(config)
    default_controller = DefaultController(config)

    # Direct controller should have unprefixed attributes
    assert hasattr(direct_controller, "timeout")
    assert not hasattr(direct_controller, "_timeout")
    assert not hasattr(direct_controller, "cfg_timeout")

    # Prefix controller should have cfg_ prefixed attributes
    assert hasattr(prefix_controller, "cfg_timeout")
    assert not hasattr(prefix_controller, "timeout")
    assert not hasattr(prefix_controller, "_timeout")

    # Default controller should have _ prefixed attributes
    assert hasattr(default_controller, "_timeout")
    assert not hasattr(default_controller, "timeout")
    assert not hasattr(default_controller, "cfg_timeout")
