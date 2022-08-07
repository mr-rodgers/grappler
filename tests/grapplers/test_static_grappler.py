from typing import Optional, Sequence

import pytest

from grappler import Package
from grappler.grapplers import StaticGrappler


@pytest.fixture
def grappler() -> StaticGrappler:
    return StaticGrappler(
        (["topic.1"], "foo"), (["topic.1", "topic.2"], "bar"), (["topic.2"], "baz")
    )


@pytest.mark.parametrize(
    "input_package, expected_package",
    [
        (None, StaticGrappler.internal_package),
        (StaticGrappler.internal_package, StaticGrappler.internal_package),
        (
            Package("Foo", "1.4.2", "grappler.grapplers.foo-test", None),
            Package("Foo", "1.4.2", "grappler.grapplers.foo-test", None),
        ),
    ],
)
def test_generates_accurate_package(
    input_package: Optional[Package], expected_package: Package
) -> None:
    grappler = StaticGrappler((["foo"], 1), package=input_package)

    plugin = next(grappler.find())
    assert plugin.package == expected_package


def test_iterated_plugin_properties(grappler: StaticGrappler) -> None:
    assert {plugin.grappler_id for plugin in grappler.find()} == {
        "grappler.grapplers.static"
    }
    assert [plugin.topics for plugin in grappler.find()] == [
        ("topic.1",),
        ("topic.1", "topic.2"),
        ("topic.2",),
    ]


@pytest.mark.parametrize(
    "topic, expected_values",
    [
        (None, ["foo", "bar", "baz"]),
        ("topic.1", ["foo", "bar"]),
        ("topic.2", ["bar", "baz"]),
        ("topic.z", []),
    ],
)
def test_find_by_topic(
    topic: str, expected_values: Sequence[str], grappler: StaticGrappler
) -> None:
    assert [grappler.load(plugin) for plugin in grappler.find(topic)] == expected_values


def test_iterated_plugins_can_be_loaded(grappler: StaticGrappler) -> None:
    assert [grappler.load(plugin) for plugin in grappler.find()] == [
        "foo",
        "bar",
        "baz",
    ]
