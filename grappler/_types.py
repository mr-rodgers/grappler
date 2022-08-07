from copy import deepcopy
from enum import Enum
from typing import (
    Any,
    Generic,
    Iterator,
    NamedTuple,
    Optional,
    Protocol,
    Tuple,
    TypeVar,
)

T = TypeVar("T")


class Package(NamedTuple):
    """
    A logical collection of plugins
    """

    name: str
    version: str
    id: str
    platform: Optional[str]


class Plugin(NamedTuple):
    """
    An external, loadable Python object
    """

    grappler_id: str
    plugin_id: str
    package: Package
    topics: Tuple[str, ...]


class Grappler(Protocol):
    @property
    def id(self) -> str:
        """A globally unique identifier for the grappler."""

    def find(self, topic: Optional[str] = None) -> Iterator[Plugin]:
        """
        Iterate over Plugins in this grappler's range.

        plugins yielded may only be yielded from this same grappler instance.
        """

    def load(self, plugin: Plugin) -> Any:
        """Load an object out of an plugin.

        May raise an UnknownPluginError if the plugin type is unknown.
        """


G_Target = TypeVar("G_Target", bound=Grappler)
G_NewTarget = TypeVar("G_NewTarget", bound=Grappler)
T_Config = TypeVar("T_Config")


class WrapperGrappler(Generic[G_Target, T_Config]):
    """
    MappableGrapper is a base class for defining grapplers which wrap
    another.

    It serves as a common base for composable grapplers, which
    [`CompositeGrappler`][grappler.grapplers.CompositeGrappler] uses remap
    and chain grapplers as necessary.

    It provides a default implementation of `find` and `load` which by
    default just wrap the targeted grappler. This behavior can be altered
    by overriding the [`filter`][grappler.WrapperGrappler.filter]
    method, or either one of those methods directly.

    Also provided is a default implementation of
    [`remapped`][grappler.WrapperGrappler.remapped].

    This is a somewhat lower-level interface that is intended use is
    as a base class. See
    [`BouncerGrappler`][grappler.grapplers.BouncerGrappler] for an example.
    ```

    """

    class FilterMode(Enum):
        """
        An enum describing whether the grappler is operating in find
        mode or load mode.
        """

        Find = "find"
        Load = "load"

    def __init__(
        self,
        target: Optional[G_Target] = None,
        *,
        config: T_Config,
    ):
        self._target = target
        self._config = config

    def find(self, topic: Optional[str] = None) -> Iterator[Plugin]:
        if self._target is None:
            raise RuntimeError(f"{self.__class__} requires a target, but none was set.")

        for plugin in self._target.find(topic=topic):
            if not self.filter(plugin, mode=self.FilterMode.Find):
                yield plugin

    def load(self, plugin: Plugin) -> Any:
        if self._target is None:
            raise RuntimeError(f"{self.__class__} requires a target, but none was set.")

        if self.filter(plugin, mode=self.FilterMode.Load):
            raise UnknownPluginError(plugin, self._target)

    def filter(self, plugin: Plugin, mode: FilterMode) -> bool:
        """
        Return whether the given plugin should be filtered out by the grappler.

        Args:
            plugin: The plugin which is currently being considered.

            mode: What operation the plugin is being considered for. When this
            is `FilterMode.find` and this function returns `True`, then the
            default `find` implementation will skip the plugin during iteration.
            When `FilterMode.load` is given and this function returns `True`,
            then the load operation will raise a
            [`UnknownPluginError`][grappler.UnknownPluginError]
        """
        return False

    def remapped(self, target: G_NewTarget) -> "WrapperGrappler[G_NewTarget, T_Config]":
        """
        Create a new grappler which uses the same config with a new target.

        Note that the default implementation assumes that the class's constructor
        supports the same interface as the default constructor. If this is not true,
        then this function should be reimplemented to perform a proper remap.

        """
        new_grappler: WrapperGrappler[G_NewTarget, T_Config] = self.__class__(  # type: ignore # noqa: E501
            target, config=deepcopy(self._config)  # type: ignore
        )
        return new_grappler

    @property
    def target(self) -> Optional[G_Target]:
        """The underlying Grappler which this one wraps."""
        return self._target

    @property
    def config(self) -> T_Config:
        """The config used by this Grappler's class."""
        return self._config


class UnknownPluginError(LookupError):
    """Raised when a grappler is asked to load an plugin it doesn't know how to."""

    def __init__(self, plugin: Plugin, grappler: Grappler) -> None:
        super().__init__(
            self,
            f"Grappler (id={repr(grappler.id)}) does not know "
            "how to load plugin: {plugin}",
        )
        self.plugin = plugin
        self.grappler = grappler
