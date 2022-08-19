import itertools
from contextlib import ExitStack
from typing import Any, Iterable, Optional, Tuple
from unittest import mock

from grappler import Grappler, Plugin
from grappler.grapplers import CompositeGrappler, StaticGrappler
from grappler.grapplers.bases import BasicGrappler


class EveryNthPluginGrappler(BasicGrappler[None]):
    def __init__(self, n: int = 1, inner: Optional[Grappler] = None):
        self._wrapped = inner
        self.n = n

    def create_iteration_context(
        self, topic: Optional[str], stack: ExitStack
    ) -> Tuple[Iterable[Plugin], Any]:
        assert self.wrapped is not None
        plugins = stack.enter_context(self.wrapped.find(topic))
        return (itertools.islice(plugins, 0, None, self.n), None)

    def load_from_context(self, plugin: Plugin, _: None) -> Any:
        assert self.wrapped is not None
        return self.wrapped.load(plugin)

    def rewrap(self, grappler: Grappler, /) -> "EveryNthPluginGrappler":
        return EveryNthPluginGrappler(self.n, grappler)

    @property
    def wrapped(self) -> Optional[Grappler]:
        return self._wrapped

    @property
    def id(self) -> str:
        return f"grappler.tests.every-{self.n}-grappler"


def test_composite_grappler_chains_grapplers_in_order() -> None:
    grappler = (
        CompositeGrappler()
        .source(StaticGrappler(*[(["numeric", "small"], i) for i in range(50)]))
        .source(StaticGrappler(*[(["numeric", "big"], i) for i in range(50, 100)]))
        .wrap(EveryNthPluginGrappler(3))
        .wrap(EveryNthPluginGrappler(2))
    )

    with grappler.find() as plugins:
        assert {grappler.load(plugin) for plugin in plugins} == set(
            range(100)[::3][::2]
        )


def test_composite_grappler_correctly_finalises_source_iterators() -> None:
    source = StaticGrappler(*[(["numeric", "small"], i) for i in range(50)])
    grappler = CompositeGrappler(source).wrap(EveryNthPluginGrappler(3))

    with ExitStack() as stack:
        create_iteration_context = stack.enter_context(
            mock.patch.object(
                source,
                "create_iteration_context",
                wraps=source.create_iteration_context,
            )
        )
        cleanup_iteration_context = stack.enter_context(
            mock.patch.object(
                source,
                "cleanup_iteration_context",
                wraps=source.cleanup_iteration_context,
            )
        )

        plugins = stack.enter_context(grappler.find())
        for _ in itertools.islice(plugins, 0, 5):
            pass

        assert create_iteration_context.call_count == 1
        assert cleanup_iteration_context.call_count == 0

    assert create_iteration_context.call_count == cleanup_iteration_context.call_count
