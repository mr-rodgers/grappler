from abc import ABC, abstractmethod
from contextlib import ExitStack
from functools import partial
from typing import Any, Dict, Generic, Iterable, Optional, Tuple, TypeVar

from grappler import Plugin

from ._basic import BasicGrappler

T_Cache = TypeVar("T_Cache")


class PluginPairGrapplerBase(
    BasicGrappler[Dict[Plugin, T_Cache]], ABC, Generic[T_Cache]
):
    """
    A grappler base that allows to pair arbitrary data with
    each iterated plugin, allowing for easier loading later.

    See [grappler.grapplers.CompositeGrappler][] for example usage.

    To implement this, you must implement the
    [`iter_plugins`][grappler.grapplers.bases.PluginPairGrapplerBase.iter_plugins] and
    [`load_with_pair`][grappler.grapplers.bases.PluginPairGrapplerBase.load_with_pair] methods.

    """  # noqa: E501

    @abstractmethod
    def iter_plugins(
        self, topic: Optional[str], exit_stack: ExitStack, /
    ) -> Iterable[Tuple[Plugin, T_Cache]]:
        """
        Return an iterator for (plugin, pair) pairs.

        It a topic is given, each iterated plugin must support it.
        If no topic is given, the any plugin may be iterated.

        The value returned for `pair` will be used with
        [`load_with_pair`][grappler.grapplers.bases.PluginPairGrapplerBase.load_with_pair]
        """

    @abstractmethod
    def load_with_pair(self, plugin: Plugin, pair: T_Cache, /) -> Any:
        """Load a plugin and return it.

        The value for `pair` is passed unmodifier from
        [`iter_plugins`][grappler.grapplers.bases.PluginPairGrapplerBase.iter_plugins]
        """

    def create_iteration_context(
        self, topic: Optional[str], exit_stack: ExitStack, /
    ) -> Tuple[Iterable[Plugin], Dict[Plugin, T_Cache]]:
        cache: Dict[Plugin, T_Cache] = {}
        return (
            map(
                partial(self.__extract_plugin_and_cache, cache),
                self.iter_plugins(topic, exit_stack),
            ),
            cache,
        )

    def load_from_context(self, plugin: Plugin, context: Dict[Plugin, T_Cache]) -> Any:
        return self.load_with_pair(plugin, context[plugin])

    def __extract_plugin_and_cache(
        self, cache: Dict[Plugin, T_Cache], pair: Tuple[Plugin, T_Cache]
    ) -> Plugin:
        plugin, cached_obj = pair
        cache[plugin] = cached_obj
        return plugin
