from abc import ABC, abstractmethod
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Generic, Iterable, Iterator, Optional, Tuple, TypeVar

from grappler._types import Plugin, UnknownPluginError

T_ItConfig = TypeVar("T_ItConfig")


class BasicGrappler(ABC, Generic[T_ItConfig]):
    """An abstract base class for a Grappler

    To properly implement this abstract class, both
    [`create_iteration_context()`][grappler.grapplers.bases.BasicGrappler.create_iteration_context]
    and
    [`load_from_context()`][grappler.grapplers.bases.BasicGrappler.load_from_context]
    must be implemented.

    In return, you will receive a class that is compliant with
    the [`Grappler`][grappler.Grappler] protocol, which uses context variables
    to isolate iterations.

    It is implemented as a generic class that allows a subclass store typed
    state before iteration, and receive it later when loading plugins.
    See [`EntryPointGrappler`][grappler.grapplers.EntryPointGrappler] source
    code for an example.
    """

    iteration_config: ContextVar[Any] = ContextVar("iteration_config")

    @property
    @abstractmethod
    def id(self) -> str:
        """Return a globally unqiue id for the grappler."""

    @abstractmethod
    def create_iteration_context(
        self, topic: Optional[str]
    ) -> Tuple[Iterable[Plugin], T_ItConfig]:
        """
        Return an iteration context for the grappler.

        It is a pair of values:

        - an iterable of plugins
        - a value that can store config for when
        [`load_from_context()`][grappler.grapplers.bases.BasicGrappler.load_from_context]
        is called.

        """
        raise NotImplementedError

    @abstractmethod
    def load_from_context(self, plugin: Plugin, context: T_ItConfig) -> Any:
        """
        Load a plugin and return its value.

        Args:
            plugin: Plugin to be loaded, which comes from the iterator
                    returned from
                    [`create_iteration_context()`][grappler.grapplers.bases.BasicGrappler.create_iteration_context]
            context: Context value which was returned from
                     `create_iteration_context`.
        """
        raise NotImplementedError

    def cleanup_iteration_context(self, context: T_ItConfig) -> None:
        """
        Cleanup an iteration context.

        This method can be used to cleanup dangling resources that
        were created in
        [`create_iteration_context()`][grappler.grapplers.bases.BasicGrappler.create_iteration_context].
        The default implementation does nothing.

        """

    @contextmanager
    def find(self, topic: Optional[str] = None) -> Iterator[Iterator[Plugin]]:
        plugins, config = self.create_iteration_context(topic)
        reset_token = self.iteration_config.set(config)

        try:
            yield iter(plugins)
        finally:
            self.iteration_config.reset(reset_token)
            self.cleanup_iteration_context(config)

    def load(self, plugin: Plugin) -> Any:
        try:
            context = self.iteration_config.get()
            return self.load_from_context(plugin, context)
        except LookupError:
            raise UnknownPluginError(plugin, self)
