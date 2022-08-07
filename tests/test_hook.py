from dataclasses import dataclass
from typing import Any, Protocol, Sequence, Type, runtime_checkable

import pytest

from grappler import Hook
from grappler.grapplers import StaticGrappler


@pytest.fixture
def static_grappler() -> StaticGrappler:
    grappler = StaticGrappler(
        (["strings"], "foo"),
        (["strings"], "bar"),
        (["strings"], "baz"),
        (["numbers", "strings"], "10"),
    )

    for i in range(10):
        grappler.add_plugin(["numbers"], i)

    return grappler


def test_empty_hook_loads_nothing(static_grappler: StaticGrappler) -> None:
    hook = Hook[Any](None, grappler=static_grappler)
    assert list(hook) == []


@pytest.mark.parametrize(
    "topic, expected_values",
    [
        ("strings", ["foo", "bar", "baz", "10"]),
        ("numbers", ["10", *range(10)]),
    ],
    ids=["strings", "numbers"],
)
def test_load_from_grappler(
    topic: str, expected_values: Sequence[Any], static_grappler: StaticGrappler
) -> None:
    assert list(Hook[Any](topic, grappler=static_grappler)) == list(expected_values)


@runtime_checkable
class Box(Protocol):
    value: Any


@dataclass
class IntBox:
    value: Any


@dataclass
class StrBox:
    value: Any


@pytest.mark.parametrize(
    "hook_topic, hook_type, expected_values",
    [
        ("numbers", int, range(10)),
        ("numbers", str, ["10"]),
        ("strings", str, ["foo", "bar", "baz", "10"]),
        ("strings", int, []),
        (
            "boxes",
            Box,
            [
                IntBox(1),
                IntBox(2),
                IntBox(3),
                StrBox("foo"),
                StrBox("bar"),
                StrBox("baz"),
            ],
        ),
        ("boxes", IntBox, [IntBox(1), IntBox(2), IntBox(3)]),
        (
            "boxes",
            StrBox,
            [
                StrBox("foo"),
                StrBox("bar"),
                StrBox("baz"),
            ],
        ),
    ],
)
def test_type_hinted_loading_ignores_non_supported_instances(
    hook_type: Type[object],
    hook_topic: str,
    expected_values: Sequence[Any],
    static_grappler: StaticGrappler,
) -> None:

    static_grappler.add_plugin(["numbers", "boxes"], IntBox(1))
    static_grappler.add_plugin(["numbers", "boxes"], IntBox(2))
    static_grappler.add_plugin(["numbers", "boxes"], IntBox(3))

    static_grappler.add_plugin(["strings", "boxes"], StrBox("foo"))
    static_grappler.add_plugin(["strings", "boxes"], StrBox("bar"))
    static_grappler.add_plugin(["strings", "boxes"], StrBox("baz"))

    # Add a non-box into the mix, to check if it will get excluded
    static_grappler.add_plugin(["boxes"], "this is not a box.")

    hook = Hook[hook_type](hook_topic, grappler=static_grappler)  # type: ignore
    assert list(hook) == list(expected_values)
