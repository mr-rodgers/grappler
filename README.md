# grappler

A library for loading plugins in Python applications.

[![Docs](https://img.shields.io/badge/Docs-mkdocs-blue?style=for-the-badge)](https://mr-rodgers.github.io/grappler/)
[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/mr-rodgers/grappler/CI?style=for-the-badge)](https://github.com/mr-rodgers/grappler/actions/workflows/main.yml)
[![PyPI](https://img.shields.io/pypi/v/grappler?logo=pypi&style=for-the-badge)](https://pypi.org/project/grappler)

## What is grappler?

Grappler is a set of tools for loading plugins into a Python
application. With it, you can load third-party plugins which
advertise along specific topics, and perform additional filtering
according to the tools provided with the library. Furthermore,
Grappler is compatible with typed Python out of the box.

## Feature highlights

- [Extremely simple interface](https://mr-rodgers.github.io/grappler/#quick-start)
  for loading entry-points out of the box.
- Extensible design, allowing implementation of new plugin sources with the
  [Grappler interface](https://mr-rodgers.github.io/grappler/api/core/#grappler.Grappler)
- [Composable API](https://mr-rodgers.github.io/grappler/user-guide/#customising-loading-with-grapplers)
  for customizing plugin sources and loading behaviour
- [Handy built-in tools](https://mr-rodgers.github.io/grappler/api/grapplers/)
  to help with customising loading behavior (e.g. blacklisting plugins so that
  their code is never loaded).

## Installation

Installation requires Python 3.8 or later.

### From PyPI

```
pip install grappler
```

## Getting Started

See the [quickstart guide](https://mr-rodgers.github.io/grappler/#quick-start)

## Documentation

Documentation can be found in project source code (as docstrings), with supplementary
documentation provided in the `docs` folder of the source distribution.

Documentation is built using [MkDocs](https://www.mkdocs.org/);
To build, run the following command:

```
pdm run mkdocs build
```

A built copy of the documentation is hosted on
https://mr-rodgers.github.io/grappler/.
