from contextlib import ExitStack
from itertools import chain
from typing import Any, Dict, Iterable, Optional, Tuple

import importlib_metadata as metadata

from grappler import Package, Plugin

from .bases import PluginPairGrapplerBase

EntryPointCache = Dict[Plugin, metadata.EntryPoint]


class EntryPointGrappler(PluginPairGrapplerBase[metadata.EntryPoint]):
    """
    A Grappler for loading objects from entry points.

    Plugins are loaded from
    [setuptools entry points](https://setuptools.pypa.io/en/latest/userguide/entry_point.html)
    installed in the Python environment. Entry point groups are mapped
    1:1 to topics.

    Currently, every `plugin.package.platform` returned from this
    grappler is `None`, even when this value is provided by underlying
    metadata.

    Additionally, the returned plugin ids are stable
    across interpreter instances; this means that the `plugin_id`
    value for a given entry point definition will be the same each time
    this grappler iterates, between different executions of a program.
    This makes the grappler suitable for use with
    [`BlacklistingGrappler`][grappler.grapplers.BlacklistingGrappler].


    Usage:

    ```python
    grappler = EntryPointGrappler()
    ```

    """  # noqa: E501

    id = "grappler.grapplers.entry_point"
    sep = "@:"
    unknown_package = Package(
        "Unknown Distribution",
        "0.0.0",
        "grappler.grapplers.entry-point-grappler.unknown-dist",
        None,
    )

    def __init__(self) -> None:
        self._groups = metadata.entry_points()

    def iter_plugins(
        self, topic: Optional[str], _: ExitStack
    ) -> Iterable[Tuple[Plugin, metadata.EntryPoint]]:
        for entry_point in self._entry_points(topic=topic):
            if entry_point.dist is None:
                package = self.unknown_package
            else:
                package = Package(
                    entry_point.dist.name,
                    version=entry_point.dist.version,
                    id=entry_point.dist._normalized_name,
                    platform=None,
                )

            plugin = Plugin(
                grappler_id=self.id,
                plugin_id=str(entry_point.value),  # type: ignore
                package=package,
                topics=(entry_point.group,),  # type: ignore
                name=str(entry_point.name),  # type: ignore
            )
            yield plugin, entry_point

    def load_with_pair(self, _: Plugin, entry_point: metadata.EntryPoint, /) -> Any:
        return entry_point.load()  # type: ignore

    def _entry_points(self, *, topic: Optional[str]) -> Iterable[metadata.EntryPoint]:
        if topic is None:
            return chain(
                *(
                    self._groups.select(group=group)  # type: ignore
                    for group in self._groups.groups
                )
            )
        else:
            return self._groups.select(group=topic)  # type: ignore
