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
    A logical collection of extensions
    """

    name: str
    version: str
    id: str
    platform: Optional[str]


class Extension(NamedTuple):
    """
    An external, loadable Python object
    """

    grappler_id: str
    extension_id: str
    package: Package
    topics: Tuple[str, ...]


class Grappler(Protocol):
    @property
    def id(self) -> str:
        """A globally unique identifier for the grappler."""

    def find(self, topic: Optional[str] = None) -> Iterator[Extension]:
        """
        Iterate over extensions in this grappler's range.

        Extensions yielded may only be yielded from this same grappler instance.
        """

    def load(self, extension: Extension) -> Any:
        """Load an object out of an extension.

        May raise an UnknownExtensionError if the extension type is unknown.
        """


class ResourcefulGrappler(Grappler, ContextManager[Grappler]):
    """A Grappler which can also be used as a context manager.

    This is a protocol for grapplers which wish to setup and teardown
    resources in `__enter__` and `__exit__` methods respectively.
    """


class UnknownExtensionError(LookupError):
    """Raised when a grappler is asked to load an extension it doesn't know how to."""

    def __init__(self, extension: Extension, grappler: Grappler) -> None:
        super().__init__(
            self,
            f"Grappler (id={repr(grappler.id)}) does not know "
            "how to load extension: {extension}",
        )
        self.extension = extension
        self.grappler = grappler
