"""
This module contains base classes for Grapplers.

[`BasicGrappler`][grappler.grapplers.bases.BasicGrappler]
provides a very barebones base to build a grappler onto. It helps
to properly implement the
[`Grappler.find`][grappler.Grappler.find] context managed interface.

"""

from ._basic import BasicGrappler
from ._plugin_pair import PluginPairGrapplerBase

__all__ = ["BasicGrappler", "PluginPairGrapplerBase"]
