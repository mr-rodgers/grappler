from typing import Any, Collection, Iterator, Optional, Tuple
from uuid import uuid4

from grappler._types import Package, Plugin, UnknownPluginError


class StaticGrappler:
    """
    A grappler for loading "plugins" supplied by the host
    application.

    This is provided as a useful tool to help modularize application
    code, so that application components can be loaded in the same
    way as plugins. To use this, supply an object as well as
    topics that each object implements to either `__init__`
    or `add_plugin`, and the grappler will generate the appropriate
    [`Plugin`][grappler.Plugin] tuples.
    The `plugin.package` is the same for every plugin yielded
    by an instance of this grappler. If a `package` argument is provided to the
    constructor, then this is used. Otherwise, a default internal
    package is used (`StaticGrappler.internal_package`).

    """

    internal_package = Package(
        "Static Plugins",
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
            Plugin(self.id, str(uuid4()), self.package, tuple(topics)): obj
            for topics, obj in objs
        }

    def add_plugin(self, topics: Collection[str], obj: Any) -> None:
        plugin = Plugin(self.id, str(uuid4()), self.package, tuple(topics))
        self.cache[plugin] = obj

    def clear(self) -> None:
        self.cache.clear()

    def find(self, topic: Optional[str] = None) -> Iterator[Plugin]:
        for plugin in self.cache:
            if topic is None or topic in plugin.topics:
                yield plugin

    def load(self, plugin: Plugin) -> Any:
        try:
            return self.cache[plugin]
        except KeyError:
            raise UnknownPluginError(plugin, self)
