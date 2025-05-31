Getting Started
===============

To build our first model, we start by creating a definition consisting of :guilabel:`soma`
and :guilabel:`basal_dendrite`.

We'll begin by defining `hh` and `pas` in the soma, and `pas` in the dendrites:

.. code-block:: python

  from arborize import define_model

  definition = define_model({
    "cable_types": {
      "soma": {
        "cable": {
          "Ra": 100,
          "cm": 1,
        },
        "mechanisms": {
          "hh": {
            "gnabar": 0.12,
            "gkbar": 0.036,
            "gl": 0.0003,
            "el": -54.3,
          },
        },
      },
      "basal_dendrite": {
        "cable": {
          "Ra": 100,
          "cm": 1,
        },
        "mechanisms": {
          "pas": {
            "g": 0.001,
            "e": -65,
          },
        },
      },
    },
  })

Next up we need to get a schematic, download
`this morphology <./_static/ball_and_stick.swc>`_
from NeuroMorpho as `morpho.swc`, then we can create a file schematic from it:

.. code-block:: python

  from arborize import file_schematic

  schematic = file_schematic("morpho.swc", definition)

.. hint::

  Arborize uses `MorphIO <https://morphio.readthedocs.io/en/latest/>`_ to load schematics
  from file. The points are labelled with the ``SectionType`` enum.

We're ready to build a cell:

.. code-block:: python

  from arborize import neuron_build

  cell = neuron_build(schematic)

.. hint::

  Arborize's NEURON builder uses `Patch <https://patch.readthedocs.io/en/latest/>`_ to
  construct NEURON objects. It provides many convenience functions.

Let's record the soma and plot the results:

.. code-block:: python

  from patch import p
  import plotly.express as px

  r = cell.soma[0].record()
  cell.basal_dendrite[0].iclamp(delay=5, duration=1, amplitude=0.1, x=1)
  t = p.time
  p.celsius = 6.3
  p.run(100)
  px.line(x=list(r), y=list(t)).show()

To create variants of your cell model, pass the template definition to ``define_model``:

.. code-block:: python

  variant = define_model(definition, {
    "cable_types": {
      "soma": {
        "mechanisms": {
          "hh": {
            "gkbar": 0.172
          }
        }
      }
    }
  })


We can now plot the difference between the 2 cell types:

.. code-block:: python

  from patch import p
  import plotly.express as px

  wildtype_schematic = file_schematic("morpho.swc", definition)
  wildtype_cell = neuron_build(schematic)
  variant_schematic = file_schematic("morpho.swc", variant)
  variant_cell = neuron_build(variant_schematic)
  wildtype_cell.basal_dendrite[0].iclamp(delay=5, duration=1, amplitude=0.1, x=1)
  variant_cell.basal_dendrite[0].iclamp(delay=5, duration=1, amplitude=0.1, x=1)
  r_wt = wildtype_cell.soma[0].record()
  r_var = variant_cell.soma[0].record()
  t = p.time
  p.celsius = 6.3
  p.run(100)
  px.line(x=list(r), y=list(t)).show()