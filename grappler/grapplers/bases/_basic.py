from abc import ABC, abstractmethod
from contextlib import ExitStack, contextmanager
from dataclasses import astuple, dataclass
from functools import partial
from typing import Any, Dict, Generic, Iterable, Iterator, Optional, Tuple, TypeVar

from grappler._types import Plugin, UnknownPluginError

T_ItConfig = TypeVar("T_ItConfig")


@dataclass(frozen=True, eq=False)
class BasicPlugin(Plugin):
    config_id: int
    wraps: Plugin

    def __eq__(self, other: object) -> bool:
        return self.as_plugin().__eq__(other)

    def __hash__(self) -> int:
        return self.as_plugin().__hash__()

    def as_plugin(self) -> Plugin:
        return Plugin(*astuple(self)[:-2])

    @classmethod
    def from_plugin(cls, config_id: int, plugin: Plugin, /) -> "BasicPlugin":
        return BasicPlugin(*astuple(plugin)[:5], config_id, plugin)  # type: ignore

    @staticmethod
    def devolve(plugin: Plugin) -> Plugin:
        if isinstance(plugin, BasicPlugin):
            return plugin.wraps
        else:
            return plugin


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

    def __init__(self) -> None:
        self.__iteration_configs: Dict[int, T_ItConfig] = {}

    @property
    @abstractmethod
    def id(self) -> str:
        """Return a globally unqiue id for the grappler."""

    @abstractmethod
    def create_iteration_context(
        self, topic: Optional[str], exit_stack: ExitStack, /
    ) -> Tuple[Iterable[Plugin], T_ItConfig]:
        """
        Return an iteration context for the grappler.

        Args:
            topic: Optionally a topic to which the iterated plugins
                   should be limited, or `None` if no limiting should
                   occur.
            exit_stack: A `contextlib.ExitStack` instance representing
                        the iteration context. This can be used to
                        setup context managers, ensuring that they will
                        be torn down at the end of the iteration context.


        The return value is a pair of values:

        - an iterable of plugins
        - a value that can store config for when
        [`load_from_context()`][grappler.grapplers.bases.BasicGrappler.load_from_context]
        is called.

        """
        raise NotImplementedError

    @abstractmethod
    def load_from_context(self, plugin: Plugin, context: T_ItConfig, /) -> Any:
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
        with ExitStack() as stack:
            plugins, config = self.create_iteration_context(topic, stack)
            config_id = id(config)

            # initialise __iteration_configs if it hasn't been already
            if not hasattr(self, "_BasicGrappler__iteration_configs"):
                self.__iteration_configs = {}

            self.__iteration_configs[config_id] = config
            stack.callback(self.cleanup_iteration_context, config)
            stack.callback(self.__iteration_configs.pop, config_id)

            yield map(partial(BasicPlugin.from_plugin, config_id), plugins)

    def load(self, plugin: Plugin) -> Any:
        try:
            if not isinstance(plugin, BasicPlugin):
                raise LookupError

            context = self.__iteration_configs[plugin.config_id]
            return self.load_from_context(BasicPlugin.devolve(plugin), context)
        except LookupError:
            raise UnknownPluginError(plugin, self)
