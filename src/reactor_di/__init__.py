"""
Reactor DI - A code generator for dependency injection in Python.

This package provides decorators based on the mediator and factory patterns
for generating dependency injection code.
"""

from importlib.metadata import version
from typing import List

__version__ = version("reactor-di")

# Import main decorators when they are added
# from .decorators import module, law_of_demeter

__all__: List[str] = [
    # "module",
    # "law_of_demeter",
]
