from multiprocessing import Pool
from typing import List, Optional

import pytest

from grappler.grapplers import EntryPointGrappler


def test_iterated_extension_semantics() -> None:
    grappler = EntryPointGrappler()

    all_extensions = [extension for extension in grappler.find()]

    # topics are mapped from entry point groups
    all_topics = {topic for ext in all_extensions for topic in ext.topics}
    assert all_topics.issuperset(["console_scripts", "pytest11"])

    # package metadata is shared among extensions from the same package
    all_packages = {ext.package for ext in all_extensions}
    assert len(all_packages) < len(all_extensions)
    assert {pkg.name for pkg in all_packages}.issuperset({"pytest"})


@pytest.mark.parametrize("topic", ["pytest11"])
def test_load_by_topics(topic: str) -> None:
    grappler = EntryPointGrappler()

    topic_extensions = [ext for ext in grappler.find(topic)]

    assert topic_extensions
    assert len(topic_extensions) < len(list(grappler.find()))

    for ext in topic_extensions:
        assert grappler.load(ext) is not None


def test_stable_extension_ids() -> None:
    host_extension_ids = load_extension_ids()

    with Pool(10) as process_pool:
        process_extension_ids = process_pool.map(load_extension_ids, range(10))

    for extension_ids in process_extension_ids:
        assert set(extension_ids) == set(host_extension_ids)


def load_extension_ids(_: Optional[int] = None) -> List[str]:
    grappler = EntryPointGrappler()
    return [ext.extension_id for ext in grappler.find()]
