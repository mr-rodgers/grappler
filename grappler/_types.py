from dataclasses import dataclass
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
    """A name for the package which may be displayed to a human."""

    version: str
    """A version number for the package."""

    id: str
    """A unique identifier for the package."""

    platform: Optional[str]
    """The package platform (sys.platform compatible value, if any)"""


@dataclass(frozen=True)
class Plugin:
    """
    An external, loadable Python object
    """

    grappler_id: str
    """The id of the grappler that the plugin came from."""

    plugin_id: str
    """A unique identifier for the plugin."""

    package: Package
    """A struct containing more information about the package
    containing the plugin"""

    topics: Tuple[str, ...]
    """A tuple of [topics](../user-guide.md#hooks-and-topics)
    that the plugin advertises."""

    name: Optional[str]
    """A name for the plugin which may be displayed to a human."""


class Grappler(Protocol):
    """General protocol for an object that can find and load plugins."""

    @property
    def id(self) -> str:
        """A globally unique identifier for the grappler."""

    def find(self, topic: Optional[str] = None) -> ContextManager[Iterator[Plugin]]:
        """
        Return a context managed iterator of plugins that this grappler
        can load.

        Implementors of this protocol only need to make sure that the
        plugins can be loaded when the returned context manager is still
        open; once the context closes, then it is not required for the
        returned plugins to still be loadable.
        """

    def load(self, plugin: Plugin) -> Any:
        """Load an object out of an plugin.

        May raise an UnknownPluginError if the plugin type is not recognised
        by the grappler.
        (This may happen even when supplied a plugin which originated in
        the grappler, but it's find context is already closed.)
        """


class UnknownPluginError(LookupError):
    """Raised when a grappler is asked to load an plugin it doesn't know how to."""

    def __init__(self, plugin: Plugin, grappler: Grappler) -> None:
        super().__init__(
            self,
            f"Grappler (id={repr(grappler.id)}) does not know "
            f"how to load plugin: {plugin}",
        )
        self.plugin = plugin
        self.grappler = grappler
