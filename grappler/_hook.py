"""
hook
====

Entry point for extensions into an application.

"""

from functools import cached_property
from typing import Any, Generator, Generic, Iterator, Optional, TypeVar, get_args

from typing_extensions import TypeGuard

from ._types import Extension, Grappler

T = TypeVar("T")


class Hook(Generic[T]):
    def __init__(self, group_name: Optional[str], grappler: Grappler) -> None:
        self.group_name = group_name
        self.grappler = grappler

    def __iter__(self) -> Iterator[T]:
        return self._iter_grappler(self.grappler)

    def grapple(self) -> Iterator[T]:
        """Load one or more extensions matching this hook."""
        return iter(self)

    def can_support(self, extension: Extension) -> bool:
        return self.group_name in extension.topics

    def _iter_grappler(self, grappler: Grappler) -> Generator[T, None, None]:
        for extension in grappler.find(self.group_name):
            if self.can_support(extension):
                loaded_obj = grappler.load(extension)
                if self.__is_valid_instance(loaded_obj):
                    yield loaded_obj

    def __is_valid_instance(self, value: Any) -> TypeGuard[T]:
        return True if self._type_arg is None else isinstance(value, self._type_arg)

    @cached_property
    def _type_arg(self) -> Any:
        cls = getattr(self, "__orig_class__", self.__class__)
        args = get_args(cls)

        if not args or args[0] == Any:
            return None

        else:
            return args[0]
