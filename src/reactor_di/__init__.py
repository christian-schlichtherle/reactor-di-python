"""
Reactor DI - A code generator for dependency injection in Python.

This package provides decorators based on the mediator and factory patterns
for generating dependency injection code.
"""

from typing import List

try:
    from importlib.metadata import version, PackageNotFoundError

    __version__ = version("reactor-di")
except (ImportError, PackageNotFoundError):
    __version__ = "0.1.0"

# Import main decorators
from .law_of_demeter import law_of_demeter
from .reactor_di import module

__all__: List[str] = [
    "module",
    "law_of_demeter",
]
