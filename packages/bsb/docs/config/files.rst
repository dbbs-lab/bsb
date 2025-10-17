###################
Configuration files
###################

A configuration file describes the components of a scaffold model. It contains the
instructions to place and connect neurons, how to represent the cells and connections as
models in simulators and what to stimulate and record in simulations.

A standard configuration file is structured like this:

.. tab-set-code::

    .. code-block:: json

      {
        "storage": {

        },
        "network": {

        },
        "morphologies": [

        ],
        "files": {

        },
        "regions": {

        },
        "partitions": {

        },
        "cell_types": {

        },
        "placement": {

        },
        "after_placement": {

        },
        "connectivity": {

        },
        "after_connectivity": {

        },
        "simulations": {

        }
      }

    .. code-block:: yaml

      storage: {}
      network: {}
      morphologies: []
      files: {}
      regions: {}
      partitions: {}
      cell_types: {}
      placement: {}
      after_placement: {}
      connectivity: {}
      after_connectivity: {}
      simulations: {}

The :guilabel:`regions`, :guilabel:`partitions`, :guilabel:`cell_types`,
:guilabel:`placement` and :guilabel:`connectivity` spaceholders hold the configuration for
:class:`Regions <bsb:bsb.topology.region.Region>`, :class:`Partitions
<bsb:bsb.topology.partition.Partition>`, :class:`CellTypes <bsb:bsb.cell_types.CellType>`,
:class:`PlacementStrategies <bsb:bsb.placement.strategy.PlacementStrategy>` and
:class:`ConnectionStrategies <bsb:bsb.connectivity.strategy.ConnectionStrategy>` respectively.

When you are configuring a model you will mostly be using configuration :ref:`attributes
<config_attrs>`, :ref:`nodes <config_nodes>`, :ref:`dictionaries <config_dict>`,
:ref:`lists <config_list>`, and :ref:`references <config_ref>`. These configuration units
can be declared through the configuration file, or programatically added.

Code
####

Most of the framework components pass the data on to Python classes, that determine the
underlying code strategy of the component. In order to link your Python classes to the
configuration file they should be an `importable module
<https://docs.python.org/3/tutorial/modules.html>`_. Here's an example of how the
``MySpecialConnection`` class in the local Python file ``connectome.py`` would be
available to the configuration:

.. code-block:: json

  {
    "connectivity": {
      "A_to_B": {
        "strategy": "connectome.MySpecialConnection",
        "value1": 15,
        "thingy2": [4, 13]
      }
    }
  }

The framework will try to pass the additional keys ``value1`` and ``thingy2`` to the
class. The class should be decorated as a configuration node for it to correctly receive
and handle the values:

.. code-block:: python

  from bsb import config, ConnectionStrategy

  @config.node
  class MySpecialConnection(ConnectionStrategy):
    value1 = config.attr(type=int)
    thingy2 = config.list(type=int, size=2, required=True)

For more information on creating your own configuration nodes see :doc:`/config/nodes`.

.. _cfg_files:

File linking
############

For some components, it might be necessary to link external files to execute their
underlying code. For instance, morphology files or density files used during cell placement.
Any files declared in the `Configuration` will be loaded and a copy will be stored in the
`Storage` of the `Scaffold` object.

In the BSB framework, we distinguish the morphology files from the other files as they
are loaded and stored differently in the `Scaffold`.
All :guilabel:`morphologies` have to be declared at the root of the `Configuration`. You can
learn more about morphologies and how to use them in :doc:`this section</morphologies/intro>`.
Regarding the rest of the files, these can be directly defined in the configuration nodes that
will use them, or you can declare them in the root component :guilabel:`files` and then refer to them
in your configuration node:

.. code-block:: json

  {
    "files": {
        "my_density_file": {
            "type": "nrrd",
            "file": "path/to/my/file.nrrd",
        }
    }
    "placement": {
      "my_placement_node": {
        "strategy": "path.to.my_strategy",
        "code_file_attr": {
            "type": "code",
            "file": "path.to.additional_code.py",
        },
        "dens_file_attr": "my_density_file",
        "other_node_attribute": 42,
      }
    }
  }

Here, both :guilabel:`code_file_attr` and :guilabel:`dens_file_attr` are
:class:`FileDependencyNodes<bsb:bsb.storage._files.FileDependencyNode>` attributes.
:guilabel:`dens_file_attr` refers to :guilabel:`my_density_file` in :guilabel:`files` using a
:ref:`reference attribute<config_ref>`, while :guilabel:`code_file_attr` is declared
directly in the node.

The advantage of declaring all your files inside the :guilabel:`files` root node is that you can reuse
them in as many nodes as you wish and they will be stored only once in the `Scaffold` object.

Parsing configuration file
##########################

The BSB uses parsers to load Configuration from external files.
Currently, the BSB supports two different file formats for configuration files:
- `JSON <https://docs.python.org/3/library/json.html>`_
- `YAML <https://pyyaml.org/wiki/PyYAMLDocumentation>`_

The configuration parser has 2 special mechanisms,
:ref:`references <cfg_file_ref>` and :ref:`imports <cfg_file_import>`. This allows parts
of the configuration file to be reusable across documents and to compose the document from
prefab blocks.

.. _cfg_file_ref:

References inside configuration files
=====================================

References point to another dictionary somewhere in the same or another document and
copy over that dictionary into the parent of the reference statement:

.. code-block:: json

  {
    "template": {
      "A": "value",
      "B": "value"
    },
    "copy": {
      "$ref": "#/template"
    }
  }

Will be parsed into:

.. code-block:: json

  {
    "template": {
      "A": "value",
      "B": "value"
    },
    "copy": {
      "A": "value",
      "B": "value"
    }
  }

.. note::

    Imported keys will not override keys that are already present. This way you can specify
    local data to customize what you import. If both keys are dictionaries, they are merged;
    with again priority for the local data.

Reference statement
-------------------

The reference statement consists of the :guilabel:`$ref` key and a 2-part value. The first
part of the statement before the ``#`` is the ``document``-clause and the second part the
``reference``-clause. If the ``#`` is omitted the entire value is considered a
``reference``-clause.

The document clause can be empty or omitted for same document references. When a document
clause is given it can be an absolute or relative path to another document (JSON or YAML).

The reference clause must be a path, either absolute or relative to a dictionary.
Paths use the ``/`` to traverse a document:

.. code-block:: json

  {
    "walk": {
      "down": {
        "the": {
          "path": {}
        }
      }
    }
  }

In this document the deepest path is ``/walk/down/the/path``.

.. warning::

    Pay attention to the initial ``/`` of the reference clause! Without it, you are making
    a reference relative to the current position. With an initial ``/`` you make a
    reference absolute to the root of the document.

.. _cfg_file_import:


Importing configuration files
=============================

Imports are the bigger cousin of the reference. They can import multiple dictionaries from
a common parent at the same time as siblings:

.. code-block:: json

  {
    "target": {
      "A": "value",
      "B": "value",
      "C": "value"
    },
    "parent": {
      "D": "value",
      "$import": {
        "ref": "#/target",
        "values": ["A", "C"]
      }
    }
  }

Will be parsed into:

.. code-block:: json

  {
    "target": {
      "A": "value",
      "B": "value",
      "C": "value"
    },
    "parent": {
      "A": "value",
      "C": "value"
    }
  }

.. note::

    If you don't specify any :guilabel:`values` all nodes will be imported.

.. note::

    The same merging rules apply as to the reference.

The import statement
--------------------

The import statement consists of the :guilabel:`$import` key and a dictionary with 2 keys:

* The :guilabel:`ref` key (note there's no ``$``) which will be treated as a reference
  statement. And used to point at the import's reference target.
* The :guilabel:`values` key which lists which keys to import from the reference target.

.. _default-config:

Default configuration
#####################

You can create a default configuration by calling :meth:`Configuration.default
<bsb:bsb.config.Configuration.default>`:

.. tab-set-code::

    .. code-block:: json

      {
        "storage": {
          "engine": "hdf5"
        },
        "network": {
          "x": 200, "y": 200, "z": 200
        },
        "partitions": {

        },
        "cell_types": {

        },
        "placement": {

        },
        "connectivity": {

        }
      }

    .. code-block:: yaml

      storage:
        engine: hdf5
      network:
        x: 200
        y: 200
        z: 200
      partitions: {}
      cell_types: {}
      placement: {}
      connectivity: {}
