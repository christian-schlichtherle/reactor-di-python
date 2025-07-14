"""
Reactor DI - A code generator for dependency injection in Python.

This package provides decorators based on the mediator and factory patterns
for generating dependency injection code.
"""

from typing import List

from .caching import CachingStrategy
from .law_of_demeter import law_of_demeter
from .module import module

__all__: List[str] = [
    "CachingStrategy",
    "law_of_demeter",
    "module",
]
