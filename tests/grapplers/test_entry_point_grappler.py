from multiprocessing import Pool
from typing import List, Optional

import pytest

from grappler.grapplers import EntryPointGrappler


def test_iterated_plugin_semantics() -> None:
    grappler = EntryPointGrappler()

    all_plugins = [plugin for plugin in grappler.find()]

    # topics are mapped from entry point groups
    all_topics = {topic for ext in all_plugins for topic in ext.topics}
    assert all_topics.issuperset(["console_scripts", "pytest11"])

    # package metadata is shared among plugins from the same package
    all_packages = {ext.package for ext in all_plugins}
    assert len(all_packages) < len(all_plugins)
    assert {pkg.name for pkg in all_packages}.issuperset({"pytest"})


@pytest.mark.parametrize("topic", ["pytest11"])
def test_load_by_topics(topic: str) -> None:
    grappler = EntryPointGrappler()

    topic_plugins = [ext for ext in grappler.find(topic)]

    assert topic_plugins
    assert len(topic_plugins) < len(list(grappler.find()))

    for ext in topic_plugins:
        assert grappler.load(ext) is not None


def test_stable_plugin_ids() -> None:
    host_plugin_ids = load_plugin_ids()

    with Pool(10) as process_pool:
        process_plugin_ids = process_pool.map(load_plugin_ids, range(10))

    for plugin_ids in process_plugin_ids:
        assert set(plugin_ids) == set(host_plugin_ids)


def load_plugin_ids(_: Optional[int] = None) -> List[str]:
    grappler = EntryPointGrappler()
    return [ext.plugin_id for ext in grappler.find()]
