from typing import Dict, Iterator, Optional, Protocol

import pytest

from grappler import Grappler, Plugin


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
