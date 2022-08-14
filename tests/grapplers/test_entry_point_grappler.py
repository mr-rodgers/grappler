from multiprocessing import Pool
from typing import List, Optional

import pytest

from grappler.grapplers import EntryPointGrappler
from tests.grapplers.conftest import PluginExtractorFunction, PluginIteratorFunction


def test_iterated_plugin_semantics(get_plugins: PluginExtractorFunction) -> None:
    grappler = EntryPointGrappler()
    plugins = get_plugins(grappler)

    # topics are mapped from entry point groups
    all_topics = {topic for ext in plugins.values() for topic in ext.topics}
    assert all_topics.issuperset(["console_scripts", "pytest11"])

    # package metadata is shared among plugins from the same package
    all_packages = {ext.package for ext in plugins.values()}
    assert len(all_packages) < len(plugins)
    assert {pkg.name for pkg in all_packages}.issuperset({"pytest"})


@pytest.mark.parametrize("topic", ["pytest11"])
def test_load_by_topics(
    topic: str,
    iter_plugins: PluginIteratorFunction,
    get_plugins: PluginExtractorFunction,
) -> None:
    grappler = EntryPointGrappler()
    count = 0

    for plugin in iter_plugins(grappler, topic):
        count += 1
        assert grappler.load(plugin) is not None

    assert count
    # plugins from topic should be fewer than all plugins in env
    assert count < len(get_plugins(grappler))


def test_stable_plugin_ids(get_plugins: PluginExtractorFunction) -> None:
    host_plugin_ids = load_plugin_ids()

    with Pool(10) as process_pool:
        process_plugin_ids = process_pool.map(load_plugin_ids, range(10))

    for plugin_ids in process_plugin_ids:
        assert set(plugin_ids) == set(host_plugin_ids)


def load_plugin_ids(_: Optional[int] = None) -> List[str]:
    grappler = EntryPointGrappler()
    with grappler.find() as it:
        return [plugin.plugin_id for plugin in it]
