# User Guide

Grappler's purpose is to provide a simple interface that you can use to load
"plugins" into your Python application. In its default configuration, it
allows you to load objects from third-party code that has been installed
into the same environment as your application.

This page explores how to use grappler to load plugins from third-party code.
Furthermore, it will examine how to use customise grappler's loading behavior.
It assumes knowledge of how to program in Python, including using type
annotations, which are required for some mid-advanced features of grappler.

## Hooks and Topics

When you need to load a third-party object (or plugin) into your application,
it is usually in order to fit a specific purpose. As such, you would expect
that each plugin you load to match a particular behaviour that you can use to invoke
it for this predetermined purpose. Furthermore, you would expect plugins to
advertise which specific behaviours they are capable of fitting, so that your
application can load and use them correctly.

[`Hooks`][grappler.Hook]
are grappler's abstraction of a particular behaviour that you wish to
load plugins for. When you need to load plugins for a particular behaviour,
you define a hook and use it to load plugins, which you can interact with
to perform the functions you need. The only requirement on the application
end, is that each hook must be given a static string identifier, which is
called the hook's topic.

Topics are simply put, a way for plugins to advertise that they are capable
of satisfying a hook's behaviour. The exact details of how this is advertised,
relies on which exact strategies grappler is using to load plugins. By
default, topics map directly to
[entry point names](
https://docs.pytest.org/en/latest/how-to/writing_plugins.html#making-your-plugin-installable-by-others
)
(from setuptools).

### Loading Plugins with Hooks

This can be done be instantiating a hook and iterating over it like a Python
iterable:

```py
from grappler import Hook


plugins = Hook("some.topic")

for plugin in plugins:
    do_something_with(plugin)
```

When you instantiate a hook, you must give it a topic to use. With the default
loading behaviour, topics map directly to entry point names. For this reason,
it is a good idea to give the topics a unique sort of prefix, so that they
do not conflict with other entry point names that may have been installed
into the environment. The pattern `pkg.module.purpose` can be a good one
to use, since your package name is already unique in the installed environment.

#### Specifying Expected Behavior

In the example above, the plugins loaded could be any arbitrary object. Provided
that your every plugin that advertises to your topic is one that implements the
behavior, then this duck-typing is not such an issue. However, you may wish to
have have stronger typing for mypy, or, you may wish to load variants of the
same plugins from the same hook. This can be accomplished by providing the hook
with a type annotation.

```python
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from grappler import Hook


topic = "grappler-docs.example.shape"


# this hook will iterate any object on this topic
hook = Hook[Any](topic)


# this hook will iterate any object that is an instance of the Shape class or its
# subclasses from the topic, and ignore all others
@dataclass
class Shape:
    area: float

hook = Hook[Shape](topic)


# this hook will iterate only objects that implements the polygon protocol from
# the topic (runtime_checkable decoration required).
@runtime_checkable
class Polygon(Protocol):
    area: float
    sides: int

hook = Hook[Polygon](topic)


# this hook will iterate circles or squares, but nothing else
@dataclass
class Circle:
    radius: float

    @property
    def area(self) -> float: ...

@dataclass
class Square:
    size: float

    @property
    def area(self) -> float: ...

hook = Hook[Circle | Square](topic)
```

Of course, these examples are contrived for extreme simplicity, but you can
define behaviors which are as complex as necessary, so long as they can be
described by a protocol or an abstract class etc.

## Grapplers

While [hooks](#hooks-and-topics) expose an interface to iterate plugins for a
particular purpose, they do not expose much about how the plugins are loaded.
Loading id done using the
[`Grappler`][grappler.Grappler] protocol. It describes an object that is able to
find plugins and their metadata, as well as load them.

Each Grappler can either act as a source for plugins, or customise the finding
or loading behavior of another grappler. For example, the
[`EntryPointGrappler`][grappler.grapplers.EntryPointGrappler] finds and loads
plugins that are installed for entry points in the Python environment, while
[`BouncerGrappler`][grappler.grapplers.BouncerGrappler] wraps another grappler
and blocks the finding or loading certain plugins depending on its
configuration.

By composing Grapplers, an application can describe a custom configuration of
how to load plugins. Furthermore, new sources of plugins can be specified by
implementing the protocol.


### Customising Loading with Grapplers

The basic [hook](#hooks-and-topics) interface shown in this guide so far uses
the default configuration. In this default config, entry points which have
been installed into the Python environment are found as plugins. There is no
caching or filtering applied.

Applications may however wish to customise this default behavior. The
[`grappler.grapplers`][grappler.grapplers] module provides a few
Grapplers which can be used to do this. The
[`CompositeGrappler`][grappler.grapplers.CompositeGrappler] is the starting
point from which to do this. It can be used to compose the plugins and
behaviors from several grapplers into a single grappler, which can then
be passed to hook in order to load plugins from:

```python
from grappler import Hook, Plugin
from grappler.grapplers import (
    BouncerGrappler,
    CompositeGrappler,
    EntryPointGrappler,
)

def block_grappler_plugins(plugin: Plugin) -> bool:
    return not plugin.package.name.startswith("grappler")

composite_grappler = (
    CompositeGrappler()
        .source(EntryPointGrappler())
        .source(YourCustomSourceGrappler())
        .wrap(BouncerGrappler())
        .configure(BouncerGrappler.checker, block_grappler_plugins)
)

plugins = Hook("some.topic", grappler=composite_grappler)

for plugin in plugins:
    do_something_with(plugin)
```

The remaining sections will explore the various Grapplers included
with the library and what you can do with them.

### Using BouncerGrappler to filter plugins

The [`BouncerGrappler`][grappler.grapplers.BouncerGrappler] provides a generic
interface that wraps another
[`Grappler`][grappler.Grappler] in order to filter the plugins that it finds
or loads. The filtering is done using checker functions, as many of which may
be supplied using
[`BouncerGrappler.checker`][grappler.grapplers.BouncerGrappler.checker].
Checker functions should simply return truthy if the the plugin should be
allowed to load.

For example, the following bouncer will block all plugins according to a
blacklist:

```python
from grappler import Package, Plugin
from grappler.grapplers import BouncerGrappler


bouncer = BouncerGrappler()
blacklisted_packages: list[Package] = [...]

@bouncer.checker
def block_plugins_in_blacklist(plugin: Plugin) -> bool:
    return plugin not in blacklisted_packages

```

Checker functions may only need to block a plugin during either
finding, or loading, but not both. To do this, use the decorator with mode
argument.

For example, the following checker can be used to deduplicate finding plugins
(when composing in such a way that creates duplicates):

```python
@bouncer.checker(mode=BouncerGrappler.Mode.Find)
def strip_duplicate_plugins(plugin: Plugin) -> bool:
    seen_plugins = context.setdefault("seen", set[Plugin]())

    if plugin in seen_plugins:
        return False

    else:
        seen_plugins.add(Plugin)
        return True
```

#### Blacklisting Plugins

The [`BlacklistingGrappler`][grappler.grapplers.BlacklistingGrappler] wraps
`BouncerGrappler`to perform more robust blacklisting than the earlier example.

Plugins can be blacklisted individually, or entire packages may be blacklisted.

```python
from typing import Iterable

from grappler import Package, Plugin
from grappler.grapplers import BlacklistingGrappler

# blacklist may either be provided statically
blacklister = BlacklistingGrappler(blacklist=[*packages_or_plugins])

# ... or dynamically
blacklister = BlacklistingGrapper()
@blacklister.blacklist
def get_blacklisted_items() -> Iterable[Plugin | Package]:
    ...

```
