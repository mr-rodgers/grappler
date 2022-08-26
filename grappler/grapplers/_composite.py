import functools
import sys
from contextlib import ExitStack
from logging import getLogger
from typing import (
    Any,
    Callable,
    Collection,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Protocol,
    Tuple,
    Type,
    TypeVar,
    cast,
    runtime_checkable,
)

from typing_extensions import Concatenate, ParamSpec

from grappler import Grappler, Plugin, UnknownPluginError

from .bases import BasicGrappler, PluginPairGrapplerBase

G_Inner = TypeVar("G_Inner", bound=Grappler)
G_Self = TypeVar("G_Self", bound=Grappler)
P_Configure = ParamSpec("P_Configure")
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
    """
    Combine plugins and behaviors from multiple grapplers.

    The types of grappler you can wrap with this are divided into two
    categories:

    - **sources** – A source grappler that provides plugins. Multiple
      of these may be provided, in which case the plugins will be chained
      in the order the grapplers were supplied in. These are provided to
      [`source()`][grappler.grapplers.CompositeGrappler.source]
    - **wrappers** – A special grappler that can act as a middleware, adding
      special behavior. Every grappler in the [grappler.grapplers][] module
      which wraps a single grappler (e.g.
      [`BouncerGrappler`][grappler.grapplers.BouncerGrappler]
      ) may be used as a wrapper.
      If there is more than one wrapper,
      then they are executed in the order which they were provided in.
      They are provided to
      [`wrap()`][grappler.grapplers.CompositeGrappler.wrap]

    """

    id = "grappler.grapplers.composite-grappler"

    def __init__(self, *sources: Grappler) -> None:
        self._sources = list(sources)
        self._wrappers: List[_WrappingGrappler] = []
        self._groups: Dict[str, List[Grappler]] = {}

    def source(
        self, source: Grappler, /, *, group: Optional[str] = None
    ) -> "CompositeGrappler":
        """Add a source to the `CompositeGrappler`.

        See [`configure_group()`][grappler.grapplers.CompositeGrappler.configure_group]
        for the meaning of `group`.
        """
        self._sources.append(source)

        if group:
            self._groups.setdefault(group, []).append(source)

        return self

    def wrap(
        self, wrapper: _WrappingGrappler, /, *, group: Optional[str] = None
    ) -> "CompositeGrappler":
        """Add a wrapper to the `CompositeGrappler`.

        The grappler will be used to wrap a virtual grappler that is
        created from all the sources. If more than one wrapper is used,
        then they will be chained in the order provided.

        See [`configure_group()`][grappler.grapplers.CompositeGrappler.configure_group]
        for the meaning of `group`.
        """
        self._wrappers.append(wrapper)

        if group:
            self._groups.setdefault(group, []).append(wrapper)

        return self

    map = wrap

    def configure(
        self,
        target: Callable[Concatenate[Any, P_Configure], Any],
        *args: P_Configure.args,
        **kwargs: P_Configure.kwargs,
    ) -> "CompositeGrappler":
        """
        Call configuration functions on matching internal grapplers.

        Grapplers are matched based on the host class of the configuration
        method passed as `target`. For example, is
        `target=BouncerGrappler.checker`
        is given, then `.checker(...)` will be called on every `BouncerGrappler`
        instance kept internally, with the given arguments.

        This method is applied immediately, and matched against the currently
        registered grapplers.

        Beware, the type definition for `target` is not fully correct.
        When using with a type checker, it is possible that this will allow
        values that will be rejected at runtime; please test thoroughly.
        """

        return self._configure(None, target, *args, **kwargs)

    def configure_group(
        self,
        group: str,
        target: Callable[Concatenate[Any, P_Configure], Any],
        /,
        *args: P_Configure.args,
        **kwargs: P_Configure.kwargs,
    ) -> "CompositeGrappler":
        """
        A version of [`configure()`][grappler.grapplers.CompositeGrappler.configure]
        for use with named groups.

        It will further narrow the matched grapplers to only those is the named
        group. Named groups are created by passing the `group` parameter to
        `source()` or `wrap()`. This allows to configure only grapplers with a
        matching group name.
        """

        return self._configure(group, target, *args, **kwargs)

    def _configure(
        self,
        group: Optional[str],
        target: Callable[Concatenate[Any, P_Configure], Any],
        *args: P_Configure.args,
        **kwargs: P_Configure.kwargs,
    ) -> "CompositeGrappler":
        targeted_type = _get_function_host_type(target)

        if targeted_type is None:
            raise ValueError(
                "Can't determine which grappler class config "
                f"function targets: {target}"
            )

        grapplers = (
            [*self._sources, *self._wrappers]
            if group is None
            else self._groups.get(group, [])
        )

        for grappler in grapplers:
            if isinstance(grappler, targeted_type):
                target(grappler, *args, **kwargs)

        return self

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


def _get_function_host_type(func: Callable[..., Any]) -> Optional[Type[Any]]:
    if func.__module__ not in sys.modules:
        return None

    module = sys.modules[func.__module__]
    parts = func.__qualname__.split(".")
    host = functools.reduce(
        lambda obj, name: getattr(obj, name, None), parts[:-1], cast(Any, module)
    )
    return host if isinstance(host, type) else None
