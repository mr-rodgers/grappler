from contextlib import ExitStack
from logging import getLogger
from typing import (
    Any,
    Collection,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Protocol,
    Tuple,
    TypeVar,
    runtime_checkable,
)

from grappler import Grappler, Plugin, UnknownPluginError

from .bases import BasicGrappler, PluginPairGrapplerBase

G_Inner = TypeVar("G_Inner", bound=Grappler)
G_Self = TypeVar("G_Self", bound=Grappler)
LOG = getLogger(__name__)


@runtime_checkable
class _WrappingGrappler(Grappler, Protocol):
    @property
    def wrapped(self) -> Optional[Grappler]:
        """Return the inner wrapped grappler."""

    def rewrap(self: G_Self, grappler: Grappler, /) -> G_Self:
        """Return a copy of the grappler which has been remapped to wrap another."""


class _MetaSourceGrappler(PluginPairGrapplerBase[Grappler]):
    id = "grappler.grapplers._internal.MetaSourceGrappler"

    # combine multiple sources into a single grappler
    def __init__(self, sources: Collection[Grappler]) -> None:
        self.sources = sources

    def iter_plugins(
        self, topic: Optional[str], stack: ExitStack
    ) -> Iterable[Tuple[Plugin, Grappler]]:
        for grappler in self.sources:
            plugins = stack.enter_context(grappler.find(topic))

            for plugin in plugins:
                yield (plugin, grappler)

    def load_with_pair(self, plugin: Plugin, grappler: Grappler, /) -> Any:
        return grappler.load(plugin)


class CompositeGrapplerIterationConfig(NamedTuple):
    source: _MetaSourceGrappler
    wrapped: Grappler


class CompositeGrappler(BasicGrappler[CompositeGrapplerIterationConfig]):
    id = "grappler.grapplers.composite-grappler"

    def __init__(self, *sources: Grappler) -> None:
        self._sources = list(sources)
        self._wrappers: List[_WrappingGrappler] = []

    def source(self, source: Grappler, /) -> "CompositeGrappler":
        """Add a source to the `CompositeGrappler`."""
        self._sources.append(source)
        return self

    def wrap(
        self, wrapper: _WrappingGrappler, /, *, name: Optional[str] = None
    ) -> "CompositeGrappler":
        """Add a wrapper to the `CompositeGrappler`.

        The grappler will be used to wrap a virtual grappler that is
        created from all the sources. If more than one wrapper is used,
        then they will be chained in the order provided.
        """
        self._wrappers.append(wrapper)
        return self

    map = wrap

    def create_iteration_context(
        self, topic: Optional[str], stack: ExitStack
    ) -> Tuple[Iterable[Plugin], Any]:
        source = _MetaSourceGrappler(self._sources)
        wrapped: Grappler = source

        for grappler in self._wrappers:
            if grappler.wrapped is not None:
                LOG.warning(
                    f"Grappler {repr(grappler.id)} already wrapping another grappler "
                    f"({repr(grappler.wrapped.id)}); currently wrapped grappler will "
                    "be discarded."
                )
            wrapped = grappler.rewrap(wrapped)

        plugins = stack.enter_context(wrapped.find(topic))
        return (plugins, CompositeGrapplerIterationConfig(source, wrapped))

    def load_from_context(
        self, plugin: Plugin, context: CompositeGrapplerIterationConfig
    ) -> Any:
        grappler: Optional[Grappler] = context.wrapped

        while grappler is not None:
            try:
                return grappler.load(plugin)
            except UnknownPluginError:
                grappler = (
                    grappler.wrapped
                    if isinstance(grappler, _WrappingGrappler)
                    else None
                )
        else:
            return context.source.load(plugin)
