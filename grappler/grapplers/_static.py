from typing import Any, Collection, Iterator, Optional, Tuple
from uuid import uuid4

from grappler._types import Extension, Package, UnknownExtensionError


class StaticGrappler:
    @staticmethod
    def internal_package() -> Package:
        return Package(
            "Static Extensions",
            "0.0.0",
            "grappler.grapplers.static.internal-package",
            None,
        )

    def __init__(
        self, *objs: Tuple[Collection[str], Any], package: Optional[Package] = None
    ) -> None:
        self.id = "grappler.grapplers.static"
        self.package = package or self.internal_package()

        self.cache = {
            Extension(self.id, str(uuid4()), self.package, tuple(topics)): obj
            for topics, obj in objs
        }

    def add_extension(self, topics: Collection[str], obj: Any) -> None:
        extension = Extension(self.id, str(uuid4()), self.package, tuple(topics))
        self.cache[extension] = obj

    def clear(self) -> None:
        self.cache.clear()

    def find(self, topic: Optional[str] = None) -> Iterator[Extension]:
        for extension in self.cache:
            if topic is None or topic in extension.topics:
                yield extension

    def load(self, extension: Extension) -> Any:
        try:
            return self.cache[extension]
        except KeyError:
            raise UnknownExtensionError(extension, self)
