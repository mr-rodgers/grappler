from contextlib import ExitStack
from typing import Any, Collection, Dict, Iterable, Optional, Tuple, TypeVar, Union
from uuid import uuid4

from grappler._types import Package, Plugin, UnknownPluginError

from .bases._basic import BasicGrappler

T_ItConfig = TypeVar("T_ItConfig")


class StaticGrappler(BasicGrappler[Dict[Plugin, Any]]):
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


    Usage:

    ```python
    grappler = StaticGrappler(
        (["list", "of", "topics"], obj),
        ...
    )
    grappler.add_plugin(["topics", "list"], obj2)
    ```

    """

    internal_package = Package(
        "Static Plugins",
        "0.0.0",
        "grappler.grapplers.static-grappler.internal-package",
        None,
    )

    def __init__(
        self, *objs: Tuple[Collection[str], Any], package: Optional[Package] = None
    ) -> None:
        self.package = package or self.internal_package

        self.cache = {
            Plugin(self.id, str(uuid4()), self.package, tuple(topics), name=None): obj
            for topics, obj in objs
        }

    def add_plugin(
        self, item: Union[Collection[str], Plugin], /, plugin_obj: Any
    ) -> None:
        """Add an static plugin to the grappler."""
        plugin = (
            item
            if isinstance(item, Plugin)
            else Plugin(self.id, str(uuid4()), self.package, tuple(item), name=None)
        )
        self.cache[plugin] = plugin_obj

    def clear(self) -> None:
        self.cache.clear()

    @property
    def id(self) -> str:
        return "grappler.grapplers.static-grappler"

    def create_iteration_context(
        self, topic: Optional[str], _: ExitStack
    ) -> Tuple[Iterable[Plugin], Dict[Plugin, Any]]:
        cache = {**self.cache}
        return (
            (plugin for plugin in cache if topic is None or topic in plugin.topics),
            cache,
        )

    def load_from_context(self, plugin: Plugin, context: Dict[Plugin, Any]) -> Any:
        try:
            return context[plugin]
        except LookupError:
            raise UnknownPluginError(plugin, self)
