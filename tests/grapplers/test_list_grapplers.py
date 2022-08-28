from typing import Any, Literal, Optional, Union
from uuid import uuid4

import pytest

from grappler import Package, Plugin
from grappler.grapplers import (
    BlacklistingGrappler,
    CompositeGrappler,
    StaticGrappler,
    WhitelistingGrappler,
)
from grappler.grapplers._list import _ListGrapplerMixin

from .conftest import PluginExtractorFunction


@pytest.fixture(params=["composite", "normal"])
def blacklisting_grappler(
    request: pytest.FixtureRequest, source_grappler: StaticGrappler
) -> Union[CompositeGrappler, BlacklistingGrappler]:
    grappler = BlacklistingGrappler(source_grappler)

    if request.param == "composite":  # type: ignore
        return CompositeGrappler().source(source_grappler).wrap(grappler)
    else:
        return grappler


@pytest.fixture(params=["composite", "normal"])
def whitelisting_grappler(
    request: pytest.FixtureRequest, source_grappler: StaticGrappler
) -> Union[CompositeGrappler, WhitelistingGrappler]:
    grappler = WhitelistingGrappler(source_grappler)

    if request.param == "composite":  # type: ignore
        return CompositeGrappler().source(source_grappler).wrap(grappler)
    else:
        return grappler


@pytest.mark.parametrize("use_function", [True, False])
def test_blacklist_plugin_by_id(
    blacklisting_grappler: Union[CompositeGrappler, BlacklistingGrappler],
    get_plugins: PluginExtractorFunction,
    use_function: bool,
) -> None:
    plugin = Plugin(
        str(uuid4()),
        str(uuid4()),
        StaticGrappler.internal_package,
        ("numbers", "blacklisted-by-id"),
        "foo-test-plugin",
    )
    second_plugin = Plugin(
        str(uuid4()),
        plugin.plugin_id,
        StaticGrappler.internal_package,
        ("foo", "bar", "blacklisted-by-id"),
        "bar-test-plugin",
    )
    add_plugin(blacklisting_grappler, plugin, 10)
    add_plugin(blacklisting_grappler, second_plugin, 10)
    add_item_to_list(
        blacklisting_grappler, (lambda: [plugin]) if use_function else plugin
    )

    found_plugins = get_plugins(blacklisting_grappler, topic="blacklisted-by-id")
    assert not found_plugins


@pytest.mark.parametrize("use_function", [True, False])
def test_blacklist_package_by_id(
    blacklisting_grappler: Union[CompositeGrappler, BlacklistingGrappler],
    get_plugins: PluginExtractorFunction,
    use_function: bool,
) -> None:
    package = Package(
        "a-test-package", "0.1.0", StaticGrappler.internal_package.id, None
    )

    assert len(get_plugins(blacklisting_grappler)) > 0

    add_item_to_list(
        blacklisting_grappler, (lambda: [package]) if use_function else package
    )

    assert len(get_plugins(blacklisting_grappler)) == 0


@pytest.mark.parametrize(
    "spec,type,match_expected",
    [
        ({"name": "a-foo-plugin"}, "plugin", True),
        ({"grappler_id": "grappler.tests.test_list_grapplers"}, "plugin", True),
        ({"topics": ["topic.foo", "topic.bar", "topic.baz"]}, "plugin", True),
        ({"topics": ["topic.foo"], "name": "a-foo-plugin"}, "plugin", True),
        ({"name": "unmatched-name"}, "plugin", False),
        (
            {
                "grappler_id": "grappler.tests.test_list_grapplers",
                "topics": ["unmatched-topic"],
            },
            "plugin",
            False,
        ),
        ({"unknown-field": True}, "plugin", False),
        ({"platform": ["linux", None]}, "package", True),
        ({"name": "a-test-package", "version": "0.1.0"}, "package", True),
        ({"name": "a-test-package", "version": ["0.1.1", "1.0.0"]}, "package", False),
    ],
)
def test_blacklist_item_structurally(
    blacklisting_grappler: Union[CompositeGrappler, BlacklistingGrappler],
    spec: Any,
    type: Literal["plugin", "package"],
    match_expected: bool,
    get_plugins: PluginExtractorFunction,
) -> None:
    test_topic = test_blacklist_item_structurally.__qualname__

    package = Package(
        "a-test-package", "0.1.0", StaticGrappler.internal_package.id, None
    )
    plugin = Plugin(
        "grappler.tests.test_list_grapplers",
        str(uuid4()),
        package,
        ("topic.foo", "topic.bar", "topic.baz", test_topic),
        "a-foo-plugin",
    )

    add_plugin(blacklisting_grappler, plugin, 10)
    add_item_to_list(blacklisting_grappler, spec, type=type)

    found_plugins = get_plugins(blacklisting_grappler, topic=test_topic)
    assert (not found_plugins) == match_expected


@pytest.mark.parametrize("use_function", [True, False])
def test_whitelist_plugin_by_id(
    whitelisting_grappler: Union[CompositeGrappler, WhitelistingGrappler],
    get_plugins: PluginExtractorFunction,
    use_function: bool,
) -> None:
    plugin = Plugin(
        str(uuid4()),
        str(uuid4()),
        StaticGrappler.internal_package,
        ("numbers",),
        "foo-test-plugin",
    )
    second_plugin = Plugin(
        str(uuid4()),
        plugin.plugin_id,
        StaticGrappler.internal_package,
        ("numbers",),
        "bar-test-plugin",
    )

    add_plugin(whitelisting_grappler, plugin, 10)
    add_plugin(whitelisting_grappler, second_plugin, 10)
    add_item_to_list(
        whitelisting_grappler, (lambda: [plugin]) if use_function else plugin
    )

    found_plugins = get_plugins(whitelisting_grappler, topic="numbers")
    assert len(found_plugins) == 1
    assert plugin.plugin_id in found_plugins
    assert found_plugins[plugin.plugin_id] in (plugin, second_plugin)


@pytest.mark.parametrize("use_function", [True, False])
def test_whitelist_package_by_id(
    whitelisting_grappler: Union[CompositeGrappler, WhitelistingGrappler],
    get_plugins: PluginExtractorFunction,
    use_function: bool,
) -> None:
    package = Package("a-test-package", "0.1.0", __name__, None)
    plugin = Plugin(
        str(uuid4()),
        str(uuid4()),
        package,
        ("numbers",),
        "foo-test-plugin",
    )

    add_plugin(whitelisting_grappler, plugin, 10)
    add_item_to_list(
        whitelisting_grappler, (lambda: [package]) if use_function else package
    )

    found_plugins = get_plugins(whitelisting_grappler, topic="numbers")
    assert len(found_plugins) == 1
    assert found_plugins[plugin.plugin_id] == plugin


@pytest.mark.parametrize(
    "spec,type,match_expected",
    [
        ({"name": "a-foo-plugin"}, "plugin", True),
        ({"grappler_id": "grappler.tests.test_list_grapplers"}, "plugin", True),
        ({"topics": ["topic.foo", "topic.bar", "topic.baz"]}, "plugin", True),
        ({"topics": ["topic.foo"], "name": "a-foo-plugin"}, "plugin", True),
        ({"name": "unmatched-name"}, "plugin", False),
        (
            {
                "grappler_id": "grappler.tests.test_list_grapplers",
                "topics": ["unmatched-topic"],
            },
            "plugin",
            False,
        ),
        ({"unknown-field": True}, "plugin", False),
        ({"platform": ["linux", None], "name": "a-test-package"}, "package", True),
        ({"name": "a-test-package", "version": "0.1.0"}, "package", True),
        ({"name": "a-test-package", "version": ["0.1.1", "1.0.0"]}, "package", False),
    ],
)
def test_whitelist_item_structurally(
    whitelisting_grappler: Union[CompositeGrappler, WhitelistingGrappler],
    spec: Any,
    type: Literal["plugin", "package"],
    match_expected: bool,
    get_plugins: PluginExtractorFunction,
) -> None:
    package = Package(
        "a-test-package", "0.1.0", StaticGrappler.internal_package.id, None
    )
    plugin = Plugin(
        "grappler.tests.test_list_grapplers",
        str(uuid4()),
        package,
        ("topic.foo", "topic.bar", "topic.baz", "numbers"),
        "a-foo-plugin",
    )

    add_plugin(whitelisting_grappler, plugin, 10)
    add_item_to_list(whitelisting_grappler, spec, type=type)

    found_plugins = get_plugins(whitelisting_grappler, topic="numbers")

    if match_expected:
        assert len(found_plugins) == 1
        assert found_plugins[plugin.plugin_id] == plugin
    else:
        assert len(found_plugins) == 0


@pytest.mark.parametrize("spec_type", ["plugin", "package"])
def test_empty_spec_raises_error(
    blacklisting_grappler: Union[CompositeGrappler, BlacklistingGrappler],
    whitelisting_grappler: Union[CompositeGrappler, BlacklistingGrappler],
    spec_type: Literal["plugin", "package"],
) -> None:
    with pytest.raises(ValueError):
        add_item_to_list(blacklisting_grappler, {}, type=spec_type)

    with pytest.raises(ValueError):
        add_item_to_list(whitelisting_grappler, {}, type=spec_type)


def add_plugin(
    grappler: Union[CompositeGrappler, WhitelistingGrappler, BlacklistingGrappler],
    plugin: Plugin,
    value: Any,
) -> None:
    if isinstance(grappler, CompositeGrappler):
        grappler.configure(StaticGrappler.add_plugin, plugin, value)
    else:
        assert isinstance(grappler.wrapped, StaticGrappler)
        grappler.wrapped.add_plugin(plugin, value)


def add_item_to_list(
    grappler: Union[CompositeGrappler, WhitelistingGrappler, BlacklistingGrappler],
    item: Any,
    type: Optional[Literal["package", "plugin"]] = None,
) -> None:
    if isinstance(grappler, CompositeGrappler):
        grappler.configure(  # type: ignore
            _ListGrapplerMixin._add_item, item, type=type
        )
    elif isinstance(grappler, BlacklistingGrappler):
        grappler.blacklist(item, type=type)  # type: ignore
    else:
        grappler.whitelist(item, type=type)  # type: ignore
