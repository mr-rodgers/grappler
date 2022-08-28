from contextlib import ExitStack
from typing import Any, Callable, Set, Type, Union

import pytest

from grappler import Grappler, Plugin
from grappler.grapplers import BouncerGrappler, CompositeGrappler, StaticGrappler

from .conftest import PluginLoaderFunction


@pytest.fixture(params=["bare", "in-composite"])
def grappler(request: Any, source_grappler: StaticGrappler) -> Grappler:
    bouncer = BouncerGrappler()

    if request.param == "bare":
        return bouncer.rewrap(source_grappler)
    else:
        return CompositeGrappler(source_grappler).wrap(bouncer)


def test_no_sources_no_find() -> None:
    grappler = BouncerGrappler()

    with grappler.find() as plugins:
        assert list(plugins) == []


def test_no_checkers_no_blocks(
    source_grappler: Grappler, load_plugins: PluginLoaderFunction
) -> None:
    grappler = BouncerGrappler(source_grappler)

    assert set(load_plugins(grappler, topic="numbers").values()) == set(range(1000))


@pytest.mark.parametrize(
    "checker,mode,expected",
    [
        (lambda i: i % 2 == 0, BouncerGrappler.Mode.FIND, set(range(1000)[::2])),
        (
            lambda i: i % 2 == 0,
            BouncerGrappler.Mode.LOAD,
            BouncerGrappler.ForbiddenPluginError,
        ),
        (lambda i: i % 2 == 0, BouncerGrappler.Mode.BOTH, set(range(1000)[::2])),
    ],
    ids=[
        "block_even_find",
        "block_even_load",
        "block_even_find_and_load",
    ],
)
def test_with_checkers(
    grappler: Grappler,
    checker: Callable[[int], bool],
    mode: BouncerGrappler.Mode,
    expected: Union[Set[int], Type[Exception]],
    load_plugins: PluginLoaderFunction,
) -> None:
    add_checker(grappler, checker, mode=mode)

    with ExitStack() as stack:

        if not isinstance(expected, set):
            stack.enter_context(pytest.raises(expected))

        assert set(load_plugins(grappler, topic="numbers").values()) == expected


def make_checker(func: Callable[[int], bool]) -> Callable[[Plugin], bool]:
    def check_plugin(plugin: Plugin) -> bool:
        val_key: str = next(
            (topic for topic in plugin.topics if topic.startswith("val-")), "val--1"
        )
        return func(int(val_key.replace("val-", "")))

    return check_plugin


def add_checker(
    grappler: Grappler, func: Callable[[int], bool], mode: BouncerGrappler.Mode
) -> None:
    assert isinstance(grappler, (CompositeGrappler, BouncerGrappler))

    if isinstance(grappler, BouncerGrappler):
        bouncers = [grappler]

    else:
        bouncers = [g for g in grappler._wrappers if isinstance(g, BouncerGrappler)]

    for bouncer in bouncers:
        bouncer.checker(make_checker(func), mode=mode)
