"""Regression tests for module + law_of_demeter integration.

These tests reproduce bugs found when using reactor-di with Pydantic-based
config classes: annotation-only fields not being forwarded, and class-level
__getattribute__ pollution from the module factory.
"""

from abc import ABC, abstractmethod
from functools import cached_property

from reactor_di import (
    CachingStrategy,
    law_of_demeter,
    module,
    thread_safe_cached_property,
)


class AnnotationOnlyConfig:
    """Config class where fields are annotations without class-level attributes.

    Mimics Pydantic BaseSettings/BaseModel behavior where:
    - hasattr(cls, field) returns False (no class-level attribute)
    - get_type_hints(cls) includes the field (it's a type annotation)
    - __init__ uses **kwargs, so has_constructor_assignment returns False
    """

    destination_topic_prefix: str
    events_queue: str
    host: str
    port: int
    timeout: int

    def __init__(self, **kwargs: object) -> None:
        for key, value in kwargs.items():
            object.__setattr__(self, key, value)


@law_of_demeter("_config")
class Processor:
    """Component with forwarded config properties and injected dependencies."""

    _config: AnnotationOnlyConfig
    _destination_topic_prefix: str
    _events_queue: str
    _producer: object
    _client: object

    def __init__(self) -> None:
        self._total = 0

    def process(self) -> str:
        return f"{self._destination_topic_prefix}:{self._events_queue}"


@law_of_demeter("_config")
class Client:
    """Another component with forwarded config properties."""

    _config: AnnotationOnlyConfig
    _host: str
    _port: int
    _events_queue: str
    _timeout: int

    def __init__(self) -> None:
        pass

    def connect(self) -> str:
        return f"{self._host}:{self._port}/{self._events_queue}"


class Producer:
    """Simple component with a forwarded config property."""

    _config: AnnotationOnlyConfig

    def __init__(self) -> None:
        pass


@module(CachingStrategy.NOT_THREAD_SAFE)
class AppModule:
    """Module that composes components with annotation-only config."""

    processor: Processor
    client: Client
    producer: Producer

    @cached_property
    def config(self) -> AnnotationOnlyConfig:
        return AnnotationOnlyConfig(
            destination_topic_prefix="test-",
            events_queue="events",
            host="localhost",
            port=6379,
            timeout=300,
        )

    def __init__(self) -> None:
        pass


# --- Tests for Bug 1: annotation-only config fields not forwarded ---


def test_annotation_only_config_forwarding_via_module():
    """Forwarded properties from annotation-only config must work through module."""
    app = AppModule()
    assert app.processor.process() == "test-:events"


def test_annotation_only_config_client_forwarding_via_module():
    """Client component forwarding must also work through module."""
    app = AppModule()
    assert app.client.connect() == "localhost:6379/events"


def test_annotation_only_config_direct_instantiation():
    """Forwarded properties must work when component is created directly.

    This is the pattern used in unit tests: create the component directly
    and set _config manually, bypassing the module factory.
    """
    config = AnnotationOnlyConfig(
        destination_topic_prefix="direct-",
        events_queue="my-queue",
        host="example.com",
        port=1234,
        timeout=60,
    )

    processor = Processor()
    processor._config = config
    assert processor._destination_topic_prefix == "direct-"
    assert processor._events_queue == "my-queue"
    assert processor.process() == "direct-:my-queue"


def test_annotation_only_config_client_direct_instantiation():
    """Client direct instantiation must also work."""
    config = AnnotationOnlyConfig(
        destination_topic_prefix="x",
        events_queue="q",
        host="redis.local",
        port=9999,
        timeout=10,
    )

    client = Client()
    client._config = config
    assert client._host == "redis.local"
    assert client._port == 9999
    assert client._events_queue == "q"
    assert client.connect() == "redis.local:9999/q"


# --- Tests for Bug 2: class-level __getattribute__ pollution ---


def test_no_class_pollution_after_module_creation():
    """Creating instances through module must not pollute the component class.

    After creating AppModule (which creates Processor through the factory),
    directly-created Processor instances must still work correctly.
    """
    # First, create through module (this used to pollute Processor.__getattribute__)
    app = AppModule()
    _ = app.processor  # Trigger factory

    # Now create directly (the old bug: patched_getattribute would chain)
    config = AnnotationOnlyConfig(
        destination_topic_prefix="manual-",
        events_queue="test-q",
        host="h",
        port=1,
        timeout=1,
    )
    processor = Processor()
    processor._config = config
    assert processor._destination_topic_prefix == "manual-"
    assert processor.process() == "manual-:test-q"


def test_multiple_module_instances_no_chaining():
    """Multiple module instances must not chain __getattribute__ on components."""
    # Create several module instances
    for _ in range(5):
        app = AppModule()
        assert app.processor.process() == "test-:events"
        assert app.client.connect() == "localhost:6379/events"

    # Direct instantiation must still work
    config = AnnotationOnlyConfig(
        destination_topic_prefix="p-",
        events_queue="eq",
        host="h",
        port=0,
        timeout=0,
    )
    client = Client()
    client._config = config
    assert client.connect() == "h:0/eq"


# --- Tests for module dependency injection ---


def test_module_injects_config_to_components():
    """Module must inject config into all components."""
    app = AppModule()
    # The processor should have _config set by the module
    assert app.processor._config is app.config


def test_module_injects_cross_component_dependencies():
    """Module must inject non-config dependencies between components."""
    app = AppModule()
    # Processor should have _producer and _client injected
    assert app.processor._producer is app.producer
    assert app.processor._client is app.client


def test_caching_strategy():
    """Cached properties should return the same instance."""
    app = AppModule()
    assert app.processor is app.processor
    assert app.client is app.client
    assert app.config is app.config


# --- Tests for Bug 3: abstract property shadows __getattr__ DI resolution ---


class CaptureBase(ABC):
    """ABC with abstract properties that match DI dependency names."""

    @property
    @abstractmethod
    def output_queue(self) -> object:
        pass

    @abstractmethod
    def run(self) -> None:
        pass


class SomeConfig:
    WIDTH: int = 1920
    HEIGHT: int = 1080


@law_of_demeter("config")
class CameraWorker(CaptureBase):
    """Component inheriting ABC abstract properties that collide with DI deps.

    `output_queue` is both an abstract property on CaptureBase
    and a DI dependency that should be injected from the module.
    """

    config: SomeConfig
    output_queue: object  # DI annotation — same name as abstract property

    _WIDTH: int
    _HEIGHT: int

    def __init__(self) -> None:
        pass

    def run(self) -> None:
        pass


@module(CachingStrategy.THREAD_SAFE)
class CameraModule:
    """Module that wires a component with abstract-property DI conflicts."""

    some_config: SomeConfig

    @thread_safe_cached_property
    def output_queue(self) -> object:
        return ["queue-sentinel"]

    camera_worker: CameraWorker

    # Alias: CameraWorker's `config` annotation resolves via name match
    @thread_safe_cached_property
    def config(self) -> SomeConfig:
        return SomeConfig()


def test_abstract_property_does_not_shadow_di_resolution():
    """DI injection must work even when the dependency name matches an abstract property.

    The ABC declares `output_queue` as an abstract @property.  CameraWorker
    declares `output_queue: object` as a DI annotation.  The @module factory
    must ensure that `camera_worker.output_queue` resolves from the module
    rather than hitting the (no longer useful) abstract property descriptor.
    """
    m = CameraModule()
    worker = m.camera_worker

    # output_queue should be the module's queue, not an abstract property error
    assert worker.output_queue == ["queue-sentinel"]
    assert worker.output_queue is m.output_queue


def test_abstract_property_di_with_law_of_demeter():
    """@law_of_demeter forwarding must also work alongside abstract property DI."""
    m = CameraModule()
    worker = m.camera_worker

    assert worker._WIDTH == 1920
    assert worker._HEIGHT == 1080


def test_abstract_property_di_direct_instantiation():
    """Direct instantiation with manual wiring must still work."""
    worker = CameraWorker()
    worker.config = SomeConfig()
    worker.__dict__["output_queue"] = "manual-queue"

    assert worker.output_queue == "manual-queue"
    assert worker._WIDTH == 1920
