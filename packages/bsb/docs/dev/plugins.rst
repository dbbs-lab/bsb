.. _plugins:

#######
Plugins
#######

The BSB is extensively extendible. While most smaller things such as a new placement or
connectivity strategy can be used simply by importing or dynamic configuration, larger
components such as new storage engines, configuration parsers or simulation backends are
added into the BSB through its plugin system.

Creating a plugin
=================

The plugin system detects pip packages that define ``entry_points`` of the plugin
category. Entry points can be specified in your package's ``setup`` using the
``entry_point`` argument. See the `setuptools documentation
<https://setuptools.readthedocs.io/en/latest/userguide/entry_point.html>`_ for a full
explanation. Here are some plugins the BSB itself registers:

.. code-block:: python

  entry_points={
      "bsb.adapters": [
          "nest = bsb.simulators.nest",
          "neuron = bsb.simulators.neuron",
      ],
      "bsb.engines": ["hdf5 = bsb.storage.engines.hdf5"],
      "bsb.config.parsers": ["json = bsb.config.parsers.json"],
  }

The keys of this dictionary are the plugin category that determine where the plugin will
be used while the strings that it lists follow the ``entry_point`` syntax:

* The string before the ``=`` will be used as the plugin name.
* Dotted strings indicate the module path.
* An optional ``:`` followed by a function name can be used to specify a function in the
  module.

What exactly should be returned from each ``entry_point`` depends highly on the plugin
category but there are some general rules that will be applied to the advertised object:

* The object will be checked for a ``__plugin__`` attribute, if present it will be used instead.
* If the object is a function (strictly a function, other callables are ignored), it will
  be called and the return value will be used instead.

This means that you can specify just the module of the plugin and inside the module set
the plugin object with ``__plugin__`` or define a function ``__plugin__`` that returns it.
Or if you'd like to register multiple plugins in the same module you can explicitly
specify different functions in the different entry points.

Examples
--------

In Python:

.. code-block:: python

    # my_pkg.plugin1 module
    __plugin__ = my_plugin

.. code-block:: python

    # my_pkg.plugin2 module
    def __plugin__():
        return my_awesome_adapter

.. code-block:: python

    # my_pkg.plugins
    def parser_plugin():
        return my_parser

    def storage_plugin():
        return my_storage

In ``setup``:

.. code-block:: python

    {
        "bsb.adapters": ["awesome_sim = my_pkg.plugin2"],
        "bsb.config.parsers": [
            "plugin1 = my_pkg.plugin1",
            "parser = my_pkg.plugins:parser_plugin"
        ],
        "bsb.engines": ["my_pkg.plugins:storage_plugin"]
    }

Categories
==========

Configuration parsers
---------------------

**Category:** ``bsb.config.parsers``

Parsers turn a configuration source (file or string) into a
:class:`Configuration <bsb:bsb.config.Configuration>`. Implementations subclass
:class:`bsb:bsb.config.parsers.ConfigurationParser`. Set ``data_description`` to
label the format for users and ``data_extensions`` to claim file extensions for
auto-detection. Bundled implementations:
:mod:`bsb_json <bsb_json:bsb_json>` and
:mod:`bsb_yaml <bsb_yaml:bsb_yaml>`.

Storage engines
---------------

**Category:** ``bsb.storage.engines``

An engine persists a reconstruction (placement, connectivity, files, morphologies)
on disk and exposes the provenance bundle that simulation results back-point to.
Implementations subclass :class:`Engine <bsb:bsb.storage.interfaces.Engine>` and
provide backend-specific :class:`FileStore <bsb:bsb.storage.interfaces.FileStore>`,
:class:`PlacementSet <bsb:bsb.storage.interfaces.PlacementSet>`,
:class:`ConnectivitySet <bsb:bsb.storage.interfaces.ConnectivitySet>` and
:class:`MorphologyRepository <bsb:bsb.storage.interfaces.MorphologyRepository>`
classes. Bundled implementations:
:class:`HDF5Engine <bsb_hdf5:bsb_hdf5.HDF5Engine>` and
:class:`FileSystemEngine <bsb:bsb.storage.fs.FileSystemEngine>`.

For the full interface contract see :ref:`storage-engine-contract`.

Simulator backends
------------------

**Category:** ``bsb.simulation_backends``

A backend translates a
:class:`Simulation <bsb:bsb.simulation.simulation.Simulation>` configuration into a
concrete simulator and runs it. Implementations subclass
:class:`SimulatorAdapter <bsb:bsb.simulation.adapter.SimulatorAdapter>` and supply
backend-specific cell models, connection models, devices, and a
:class:`SimulationResult <bsb:bsb.simulation.results.SimulationResult>` subclass.
Bundled implementations:
:mod:`bsb_nest <bsb_nest:bsb_nest>`,
:mod:`bsb_neuron <bsb_neuron:bsb_neuron>`,
:mod:`bsb_arbor <bsb_arbor:bsb_arbor>`.

Components
----------

**Category:** ``bsb.components``

Using component plugins, plugin authors can distribute reusable components. You can
either eagerly load your components by loading the module, or lazy load them by
registering a classmap extension:

.. code-block:: toml

   [project.entry-points."bsb.components"]
   my_components = "my_package.my_module:classmap"

And in ``my_package/my_module.py`` you can give a ``classmap`` dictionary that is
keyed by the fully qualified class name of the components's classmaps you would like to
extend. E.g., to add a placement strategy:

.. code-block:: python

   classmap = {
     "bsb.placement.strategy.PlacementStrategy": {
       "super_placement": "my_package.placement_module.SuperPlacementStrategy"
     }
   }

A user can then use this placement strategy as follows:

.. code-block:: python

   strat = PlacementStrategy(strategy="super_placement", ...)
