from typing import Any, Dict, Iterator, Optional, Protocol

import pytest

from grappler import Grappler, Plugin
from grappler.grapplers import StaticGrappler

_PLUGINS = [*[(["numbers", f"val-{i}"], i) for i in range(1000)]]


class PluginIteratorFunction(Protocol):
    def __call__(
        self, grappler: Grappler, topic: Optional[str] = None
    ) -> Iterator[Plugin]:
        ...


class PluginExtractorFunction(Protocol):
    def __call__(
        self, grappler: Grappler, topic: Optional[str] = None
    ) -> Dict[str, Plugin]:
        ...


class PluginLoaderFunction(Protocol):
    def __call__(
        self, grappler: Grappler, topic: Optional[str] = None
    ) -> Dict[Plugin, Any]:
        ...


@pytest.fixture
def iter_plugins() -> PluginIteratorFunction:
    def find_plugins(
        grappler: Grappler, topic: Optional[str] = None
    ) -> Iterator[Plugin]:
        with grappler.find(topic) as plugins:
            for plugin in plugins:
                yield plugin

    return find_plugins


@pytest.fixture
def get_plugins(iter_plugins: PluginIteratorFunction) -> PluginExtractorFunction:
    def find_plugins(
        grappler: Grappler, topic: Optional[str] = None
    ) -> Dict[str, Plugin]:
        return {plugin.plugin_id: plugin for plugin in iter_plugins(grappler, topic)}

    return find_plugins


@pytest.fixture
def load_plugins(iter_plugins: PluginIteratorFunction) -> PluginLoaderFunction:
    def _load(grappler: Grappler, topic: Optional[str] = None) -> Dict[Plugin, Any]:
        return {
            plugin: grappler.load(plugin) for plugin in iter_plugins(grappler, topic)
        }

    return _load


@pytest.fixture
def source_grappler() -> StaticGrappler:
    return StaticGrappler(*_PLUGINS)
