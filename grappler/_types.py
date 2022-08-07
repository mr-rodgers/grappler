from typing import (
    Any,
    ContextManager,
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


class ResourcefulGrappler(Grappler, ContextManager[Grappler]):
    """A Grappler which can also be used as a context manager.

    This is a protocol for grapplers which wish to setup and teardown
    resources in `__enter__` and `__exit__` methods respectively.
    """


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
