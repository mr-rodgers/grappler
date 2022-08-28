from typing import (
    Callable,
    Collection,
    List,
    Literal,
    Optional,
    Tuple,
    TypedDict,
    TypeVar,
    Union,
    cast,
    overload,
)

from grappler import Grappler, Package, Plugin

from ._bouncer import BouncerGrappler

G_Listing = TypeVar("G_Listing", bound="_ListGrapplerMixin")


class PluginSpec(TypedDict, total=False):
    grappler_id: str
    plugin_id: str
    topics: Tuple[str, ...]
    name: str


class PackageSpec(TypedDict, total=False):
    name: str
    version: str
    id: str
    platform: Optional[str]


PluginAndPackageListFactory = Callable[[], Collection[Union[Plugin, Package]]]


class _ListGrapplerMixin:
    plugin_items: List[PluginSpec]
    package_items: List[PackageSpec]
    dynamic_items: List[PluginAndPackageListFactory]

    def __init__(self, items: Collection[Union[Plugin, Package]]) -> None:
        self.plugin_items = []
        self.package_items = []
        self.dynamic_items = []

        for item in items:
            self._add_item(item)

    @overload
    def _add_item(self, item: Union[Plugin, Package], /) -> None:
        ...

    @overload
    def _add_item(
        self, item: PluginAndPackageListFactory, /
    ) -> PluginAndPackageListFactory:
        ...

    @overload
    def _add_item(self, item: PluginSpec, /, *, type: Literal["plugin"]) -> None:
        ...

    @overload
    def _add_item(self, item: PackageSpec, /, *, type: Literal["package"]) -> None:
        ...

    def _add_item(
        self,
        item: Union[
            Plugin,
            Package,
            PluginAndPackageListFactory,
            PluginSpec,
            PackageSpec,
        ],
        /,
        *,
        type: Optional[Literal["plugin", "package"]] = None,
    ) -> Union[PluginAndPackageListFactory, None]:
        """Add an item to the whitelist."""
        if isinstance(item, Plugin):
            return self._add_item({"plugin_id": item.plugin_id}, type="plugin")
        elif isinstance(item, Package):
            return self._add_item({"id": item.id}, type="package")
        elif isinstance(item, dict):
            if type is None:
                raise TypeError(
                    "A type must be specified when using a dictionary specification."
                )
            elif not item:
                raise ValueError(
                    "An empty dictionary specification is not allowed (useless)."
                )
            elif type == "plugin":
                self.plugin_items.append(cast(PluginSpec, item))
            else:
                self.package_items.append(cast(PackageSpec, item))
            return None
        else:
            self.dynamic_items.append(item)
            return item

    def _is_listed(self, plugin: Plugin) -> bool:
        dynamic_items = {
            plugin_or_pkg
            for factory in self.dynamic_items
            for plugin_or_pkg in factory()
        }
        plugin_specs = [
            *self.plugin_items,
            *(
                PluginSpec(plugin_id=item.plugin_id)
                for item in dynamic_items
                if isinstance(item, Plugin)
            ),
        ]
        package_specs = [
            *self.package_items,
            *(
                PackageSpec(id=item.id)
                for item in dynamic_items
                if isinstance(item, Package)
            ),
        ]

        for plugin_spec in plugin_specs:
            if self._matches_spec(plugin_spec, plugin):
                return True

        for package_spec in package_specs:
            if self._matches_spec(package_spec, plugin.package):
                return True

        return False

    @overload
    def _matches_spec(self, spec: PluginSpec, item: Plugin) -> bool:
        ...

    @overload
    def _matches_spec(self, spec: PackageSpec, item: Package) -> bool:
        ...

    def _matches_spec(
        self,
        spec: Union[PluginSpec, PackageSpec],
        item: Union[Plugin, Package],
    ) -> bool:
        for field, spec_val in spec.items():
            if not hasattr(item, field):
                return False

            item_val = getattr(item, field)

            if not isinstance(spec_val, str) and isinstance(spec_val, Collection):
                if not isinstance(item_val, str) and isinstance(item_val, Collection):
                    if not set(spec_val).issubset(item_val):
                        return False
                    else:
                        continue
                elif item_val not in spec_val:
                    return False
            elif spec_val != item_val:
                return False
        else:
            return True

    def _copy_config(self, other: G_Listing) -> G_Listing:
        other.dynamic_items[:] = self.dynamic_items
        other.package_items[:] = self.package_items
        other.plugin_items[:] = self.plugin_items
        return other


class BlacklistingGrappler(BouncerGrappler, _ListGrapplerMixin):
    """
    A grappler which allows to blacklist plugins or packages.

    Blacklisted plugins will be blocked from iteration and loading.
    When a package is blacklisted, *all* plugins from it will be
    blocked.
    """

    def __init__(
        self,
        inner: Optional[Grappler] = None,
        items: Collection[Union[Plugin, Package]] = (),
    ) -> None:
        BouncerGrappler.__init__(self, inner)
        _ListGrapplerMixin.__init__(self, items)

        # Install BouncerGrappler.checker to reject listed plugins
        self.checker(self._is_not_listed)

    def _is_not_listed(self, plugin: Plugin) -> bool:
        return not self._is_listed(plugin)

    def rewrap(self, grappler: Grappler, /) -> "BlacklistingGrappler":
        return self._copy_config(BlacklistingGrappler(grappler))

    blacklist = _ListGrapplerMixin._add_item
    """Add an item to the blacklist.

    The grappler will skip any plugins that matches a blacklisted
    item, ensuring that they will not be loaded.

    This is an instance method with the following signatures:

    ```python
    grappler.blacklist(plugin_or_package: Union[Plugin, Package]) -> None:
        ...

    @grappler.blacklist
    def get_blacklisted_plugins() -> List[Union[Plugin, Package]]:
        return [...]
    ```

    These forms will blacklist plugins or entire packages *by their ids*.
    This means that no attempts will be made to match names or any other
    fields on the plugin on package before blocking it.

    ## Structural matching

    There are two additional signatures which perform a somewhat more
    structural matching (and therefore blacklisting) of plugins and packages
    using dictionary specifications:

    ```python
    grappler.blacklist({"name": "a-plugin-name", "topics": ["pytest11"]},
                        type="plugin")
    grappler.blacklist({"platform": ["win32", "mac"]}, type="package")
    ```

    In this form, a dictionary spec is given for matching, as well as the
    `type` argument. `type` must be passed as a keyword and must be either
    `"plugin"` or `"package"`, indicating what kind of specification is
    being passed in.

    A type of structural matching is performed on the item, in order to
    determine if each encountered plugin/package should be blacklisted.
    Every field in the dictionary is checked as an attribute of either
    the [plugin][grappler.Plugin] or [package][grappler.Package], and
    a match is determined based on these rules:

    1. If the attribute is not present on the plugin/package, there is
       no match.

    2. If the field in the specification is a python collection:
        1. if the attribute is also a collection, then it matches
            only when the attribute is a superset of the specified
            collection. e.g. the `"topics"` field of the plugin
            specification above can match plugins which have
            `plugin.topics == ("pytest11",)`  or
            `plugin.topics == ("foo", "pytest11", "bar")` etc.

        2. if the attribute is not a collection, then it matches
            only when the attribute is contained within
            e.g. the package specification above will
            blacklist only packages that either have
            `package.platform == 'win32'` or `package.platform == 'mac'`.

    3. In all other cases, a match only occurs when the attribute is
       equal to the field specification.

    All fields in the specification must match a plugin/package for it
    to be blacklisted.
    """


class WhitelistingGrappler(BouncerGrappler, _ListGrapplerMixin):
    """
    A grappler which allows to whitelist plugins or packages
    """

    def __init__(
        self,
        inner: Optional[Grappler] = None,
        items: Collection[Union[Plugin, Package]] = (),
    ) -> None:
        BouncerGrappler.__init__(self, inner)
        _ListGrapplerMixin.__init__(self, items)

        # Install BouncerGrappler.checker to reject non listed plugins
        self.checker(self._is_listed)

    def rewrap(self, grappler: Grappler, /) -> "WhitelistingGrappler":
        return self._copy_config(WhitelistingGrappler(grappler))

    whitelist = _ListGrapplerMixin._add_item
    """
    Add an item to the whitelist.

    The grappler will skip all items unless they are in the whitelist.

    This function has the same signature as
    [BlacklistingGrappler.blacklist()][grappler.grapplers.BlacklistingGrappler.blacklist]
    """
