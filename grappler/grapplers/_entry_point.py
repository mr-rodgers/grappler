from itertools import chain
from typing import Any, Iterable, Iterator, Optional

import importlib_metadata as metadata

from grappler import Grappler, Package, Plugin, UnknownPluginError

from ._static import StaticGrappler


class EntryPointGrappler(Grappler):
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

    """  # noqa: E501

    id = "grappler.grapplers.entry_point"
    sep = "@:"

    def __init__(self) -> None:
        self._groups = metadata.entry_points()

    def find(self, topic: Optional[str] = None) -> Iterator[Plugin]:
        for entry_point in self._entry_points(topic=topic):
            if entry_point.dist is None:
                package = StaticGrappler.internal_package
            else:
                package = Package(
                    entry_point.dist.name,
                    version=entry_point.dist.version,
                    id=entry_point.dist._normalized_name,
                    platform=None,
                )

            yield Plugin(
                grappler_id=self.id,
                plugin_id=self.sep.join(
                    (
                        entry_point.name,  # type: ignore
                        entry_point.value,  # type: ignore
                        entry_point.group,  # type: ignore
                    )
                ),
                package=package,
                topics=(entry_point.group,),  # type: ignore
            )

    def load(self, plugin: Plugin) -> Any:
        splits = plugin.plugin_id.split(self.sep)

        if len(splits) != 3:
            raise UnknownPluginError(plugin, self)

        name, value, group = splits
        entry_point = metadata.EntryPoint(
            name=name,
            value=value,
            group=group,
        )  # type: ignore
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
