from typing import Callable, Union

from .caching import CachingStrategy


def module(
    cls_or_strategy: Union[type, CachingStrategy, None] = None, /
) -> Union[type, Callable[[type], type]]:
    ...
