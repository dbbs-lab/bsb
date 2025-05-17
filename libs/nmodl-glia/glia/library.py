"""
    Import this module to load the Glia library into neuron::

        import glia, glia.library

    Glia is now operational!
"""

from . import _manager

_manager.load_library()
