from functools import cached_property
from typing import (
    Any,
    Collection,
    Generator,
    Generic,
    Iterator,
    Optional,
    Set,
    TypeVar,
    get_args,
)

from typing_extensions import TypeGuard

from ._types import Grappler, Plugin
from .grapplers import EntryPointGrappler

T = TypeVar("T")


class Hook(Generic[T]):
    """
    An abstraction for loading plugins providing a specific behavior.

    Hooks provide an iterable interface for loaded plugin values. This
    allows to define a hook with a topic to load plugins for, and then
    iterate over the hook in order to access the externally loaded
    objects. Furthermore, the iterated objects can be further restricted
    by providing a type argument to the hook; when this is done, any
    externally loaded object that is not an instance of the given type
    is skipped.

    Important: Type arguments to Hook must be usable in `isinstance` check
        The type argument given to the hook class should be
        usable as the second argument to Python's `isinstance`.
        Failing this constraint will result in a type error upon
        iteration (notable exception: `Any` may be used). This means that
        some types which are otherwise valid are not usable in this context
        (e.g. `None` or `Callable[...]`).

    Args:
        topic: An arbitrary string identifier for the behavior that your
               hook will load plugins for. The hook will then only load
               plugins that advertise the topic given here.
        grappler: When given, it should be a
                  [`Grappler`][grappler.Grappler] which will be used to
                  find and load plugins. If not given, then an unmodified
                  instance of
                  [`EntryPointGrappler`][grappler.grapplers.EntryPointGrappler]
                  is used. See the
                  [Customising Loading](../user-guide.md#customising-loading-with-grapplers)
                  section of the user guide, which gives an explanation of how
                  to setup a grappler for more complex loading behavior.

    Usage:
    ```python
    # iterate the hook to load all plugins from the topic.
    from grappler import Hook
    objs = list(Hook("topic.counter-functions"))
    ```

    ```python
    # use a type argument to restrict the objects that are returned.
    from typing import Any, Protocol, runtime_checkable
    from grappler import Hook

    @runtime_checkable
    class CounterFunction(Protocol):
        def __call__(self, items: Any) -> int: ...

    counter_functions = list(Hook[CounterFunction]("topic.counter-functions"))
    # (note: argument specs are not checked for callable Protocol
    # instance checks; the mere presence of a `__call__` method will satisfy
    # the hook's filter. This is due to how `isinstance` works in Python.)

    ```

    """  # noqa

    def __init__(self, topic: str, *, grappler: Optional[Grappler] = None) -> None:
        self.topic = topic
        self.grappler = grappler or EntryPointGrappler()
        self._loaded: Set[Plugin] = set()

    def __iter__(self) -> Iterator[T]:
        """Return an iterator to loaded plugin objects from the hook's topic.

        If the hook was instantiated with a type argument, then only objects
        which pass `isinstance(obj, T)` are included in the iterator.
        """
        return self._iter_grappler(self.grappler)

    @property
    def loaded_plugins(self) -> Collection[Plugin]:
        """
        Return a collection containing all plugins loaded by the hook
        so far.
        """
        return list(self._loaded)

    def can_support(self, plugin: Plugin) -> bool:
        return self.topic in plugin.topics

    def _iter_grappler(self, grappler: Grappler) -> Generator[T, None, None]:
        with grappler.find(self.topic) as plugins:
            for plugin in plugins:
                if not self.can_support(plugin):
                    continue

                loaded_obj = grappler.load(plugin)
                self._loaded.add(plugin)

                if self.__is_valid_instance(loaded_obj):
                    yield loaded_obj

    def __is_valid_instance(self, value: Any) -> TypeGuard[T]:
        return True if self._type_arg is None else isinstance(value, self._type_arg)

    @cached_property
    def _type_arg(self) -> Any:
        cls = getattr(self, "__orig_class__", self.__class__)
        args = get_args(cls)

        if not args or args[0] == Any:
            return None

        else:
            return args[0]
