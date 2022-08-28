from contextlib import ExitStack
from enum import Enum
from logging import getLogger
from typing import (
    Any,
    Callable,
    Iterator,
    List,
    Literal,
    Optional,
    Protocol,
    Tuple,
    TypedDict,
    TypeVar,
    Union,
    overload,
)

from grappler import Grappler, Plugin

from .bases import PluginPairGrapplerBase

LOG = getLogger(__name__)
F_Checker = TypeVar("F_Checker", bound="BounceCheck")


class InvalidConfigurationError(TypeError):
    def __init__(self, grappler: Grappler) -> None:
        super().__init__(
            "Attempting to load a plugin, but no inner grappler "
            f"is configured: {repr(grappler)}"
        )
        self.grappler = grappler


class ForbiddenPluginError(RuntimeError):
    def __init__(self, plugin: Plugin, grappler: Grappler) -> None:
        super().__init__(
            "Loading this plugin is forbidden by the bouncer "
            f"configuration: {plugin}"
        )
        self.plugin = plugin
        self.grappler = grappler


class BounceCheck(Protocol):
    """A callable that is used to determine if a plugin should be bounced.

    If this callable returns `True`, then the bounce checker will block
    the plugin from being iterated and/or loaded.
    """

    def __call__(self, plugin: Plugin, /) -> bool:
        """Return whether this plugin should be bounced."""


Checks = TypedDict("Checks", {"find": List[BounceCheck], "load": List[BounceCheck]})


class BouncerGrappler(PluginPairGrapplerBase[None]):
    """
    Restrict plugins from an inner grappler based on rules
    defined as predicates.
    """

    id = "grappler.grapplers.bouncer"

    ForbiddenPluginError = ForbiddenPluginError

    class Mode(Enum):
        """Operating mode for checker functions."""

        FIND = "find"
        """For checker functions that should only be used during the grappler's
        scan operation. A plugin that is blocked during this operation will
        never be seen by grappler's client."""

        LOAD = "load"
        """For checker functions that should only be used during the grappler's
        load operation. If a plugin is blocked during this operation, an
        exception will be raised when attempting to load it."""

        BOTH = "both"

    def __init__(self, inner: Optional[Grappler] = None) -> None:
        self.wrapped = inner
        self._checks = Checks(find=[], load=[])

    def rewrap(self, grappler: Grappler, /) -> "BouncerGrappler":
        bouncer = BouncerGrappler(grappler)
        bouncer._checks = Checks(find=self._checks["find"], load=self._checks["load"])
        return bouncer

    def _is_allowed(self, plugin: Plugin, *, mode: Literal["find", "load"]) -> bool:
        for bounce_check in self._checks[mode]:
            if not bounce_check(plugin):
                LOG.debug(f"{plugin} rejected by bounce check: {bounce_check}")
                return False
        else:
            return True

    def iter_plugins(
        self, topic: Optional[str], exit_stack: ExitStack, /
    ) -> Iterator[Tuple[Plugin, None]]:
        if not self.wrapped:
            LOG.warning(
                "Attempting to use `BouncerGrappler` without an inner grappler."
            )
            return iter([])
        else:
            plugins = exit_stack.enter_context(self.wrapped.find(topic))
            return (
                (plugin, None)
                for plugin in plugins
                if self._is_allowed(plugin, mode="find")
            )

    def load_with_pair(self, plugin: Plugin, _: None, /) -> Any:
        if not self.wrapped:
            raise InvalidConfigurationError(self)
        elif not self._is_allowed(plugin, mode="load"):
            raise ForbiddenPluginError(plugin, self)
        else:
            return self.wrapped.load(plugin)

    @overload
    def checker(self, checker: F_Checker, /, *, mode: Mode = Mode.BOTH) -> F_Checker:
        ...

    @overload
    def checker(self, *, mode: Mode) -> Callable[[F_Checker], F_Checker]:
        ...

    def checker(
        self, checker: Optional[F_Checker] = None, *, mode: Mode = Mode.BOTH
    ) -> Union[F_Checker, Callable[[F_Checker], F_Checker]]:
        """Register a checker function for the bouncer.

        This function can be used as a decorator, or called directly:

        ```python
        bouncer = BouncerGrappler(...)

        @bouncer.checker
        def check_plugin(plugin: Plugin) -> bool
            ...

        @bouncer.checker(mode=bouncer.Mode.LOAD)
        def check_before_loading_only(plugin: Plugin) -> bool
            ...

        def check_during_find_only(plugin: Plugin) -> bool:
            ...
        bouncer.checker(check_during_find_only, mode=bouncer.Mode.FIND)
        ```
        """

        def decorate(f: F_Checker) -> F_Checker:
            if mode in (self.Mode.FIND, self.Mode.BOTH):
                self._checks["find"].append(f)
            elif mode in (self.Mode.LOAD, self.Mode.BOTH):
                self._checks["load"].append(f)
            else:
                raise ValueError(f"Invalid check mode: {mode}")
            return f

        if checker is not None:
            return decorate(checker)
        else:
            return decorate
