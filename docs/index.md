# Quick Start

grappler provides a way to load plugins into Python 3.8+
applications. Plugins are third party code that provide
a function that your application needs. With grappler, you
can easily iterate through plugins by topic and seamlessly
filter by object types that your program is able to handle.

## Usage

grappler provides a `Hook` interface which can be used to
specific a topic to iterate plugin objects:

```python
from abc import ABC, abstractmethod
from grappler import Hook


class Surface(ABC):
    @abstractmethod
    def paint(self, context: dict[str, int]) -> None:
        """Paint onto the surface with the given context."""

hook = Hook[Surface](topic="your.app.topics.surface")

for surface in hook:
    surface.paint({...})
```

grappler supports type hints, and the surface
objects returned from the hook above will be hinted as `Surface`
instances.

You can furthermore load any type of object you want from
an plugin. To do this, don't provide any type hint to
the constructor (or use `Any`):

```python
hook = Hook("your.app.topics.printables")
for obj in hook:
    print(f"Loaded object of type: {type(obj)}")
```
