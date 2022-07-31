from typing import Any, Collection, Iterator, Optional, Tuple
from uuid import uuid4

from grappler._types import Extension, Package, UnknownExtensionError


class StaticGrappler:
    """
    A grappler for loading "extensions" supplied by the host
    application.

    This is provided as a useful tool to help modularize application
    code, so that application components can be loaded in the same
    way as extensions. To use this, supply an object as well as
    topics that each object implements to either `__init__`
    or `add_extension`, and the grappler will generate the appropriate
    [`Extension`][grappler.Extension] tuples.

    The `extension.package` is the same for every extension yielded
    by an instance of this grappler. If a `package` argument is provided to the
    constructor, then this is used. Otherwise, a default internal
    package is used (`StaticGrappler.internal_package`).

    """

    internal_package = Package(
        "Static Extensions",
        "0.0.0",
        "grappler.grapplers.static.internal-package",
        None,
    )

    def __init__(
        self, *objs: Tuple[Collection[str], Any], package: Optional[Package] = None
    ) -> None:
        self.id = "grappler.grapplers.static"
        self.package = package or self.internal_package

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
