##################
List of strategies
##################

:class:`AllToAll <bsb:bsb.connectivity.general.AllToAll>`
=========================================================

This strategy creates a connection with a probability equals to ``affinity``
for each possible pair of presynaptic and postsynaptic neurons.
By default, all unique neuron pair create one connection.

* ``affinity``: Probability of a pair of neuron to create a connection (default is 1.0, i.e. all connected).

:class:`FixedIndegree <bsb:bsb.connectivity.general.FixedIndegree>`
===================================================================

This strategy connects to each postsynaptic neuron, a fixed number of uniform randomly selected
presynaptic neurons.

* ``indegree``: Number of neuron to connect for each postsynaptic neuron.

.. tab-set-code::

    .. code-block:: json

           "connectivity": {
           "A_to_B": {
               "strategy": "bsb.connectivity.FixedIndegree",
               "presynaptic": {
                       "cell_types": ["A"]
               },
               "postsynaptic": {
                       "cell_types": ["B"]
               },
               "indegree": 2
           }

    .. code-block:: python

      config.connectivity.add(
        "A_to_B",
        strategy="bsb.connectivity.FixedIndegree",
        presynaptic=dict(cell_types=["A"]),
        postsynaptic=dict(cell_types=["type_B"]),
        indegree= 2
      )

.. note::
  In this example every cell of type B is connected to two cells of type A.


:class:`FixedOutdegree <bsb:bsb.connectivity.general.FixedOutdegree>`
=====================================================================

This strategy connects to each presynaptic neuron, a fixed number of uniform randomly selected
postsynaptic neurons.

* ``outdegree``: Number of neuron to connect for each presynaptic neuron.

:class:`VoxelIntersection <bsb:bsb.connectivity.detailed.voxel_intersection.VoxelIntersection>`
===============================================================================================

This strategy voxelizes morphologies into collections of cubes, thereby reducing the
spatial specificity of the provided traced morphologies by grouping multiple compartments
into larger cubic voxels. Intersections are found not between the separate compartments
but between the voxels and random compartments of matching voxels are connected to each other.
This means that the connections that are made are less specific to the exact morphology
and can be very useful when only 1 or a few morphologies are available to represent each
cell type.

* ``affinity``: A fraction between 1 and 0 which indicates the tendency of cells to form
  connections with other cells with whom their voxels intersect. This can be used to
  downregulate the amount of cells that any cell connects with.
* ``contacts``: A number or distribution determining the amount of synaptic contacts one
  cell will form on another after they have selected eachother as connection partners.

.. note::
  The affinity only affects the number of cells that are contacted, not the number of
  synaptic contacts formed with each cell.

.. tab-set-code::

    .. code-block:: json

        {
          "A_to_B": {
            "strategy": "bsb.connectivity.VoxelIntersection",
            "presynaptic": {
              "cell_types": [
                "A"
              ],
            },
            "postsynaptic": {
              "cell_types": [
                "B"
              ],
            },
            "affinity": 0.5,
            "contacts": 1
          }
        }

    .. code-block:: python

      config.connectivity.add(
        "A_to_B",
         strategy="bsb.connectivity.VoxelIntersection",
         presynaptic=dict(cell_types=["A"]),
         postsynaptic=dict(cell_types=["type_B"]),
         affinity= 0.5,
         contacts= 1
      )

The previous example demonstrates a strategy to connect cells of type A with cells of type B,
where only half of the computed overlaps are considered, and one synapse is placed for each connection.
It is also possible to define the number of synapse per connection with a distribution:

.. tab-set-code::

    .. code-block:: json

            {
          "A_to_B": {
            "strategy": "bsb.connectivity.VoxelIntersection",
            "presynaptic": {
              "cell_types": [
                "A"
              ],
            },
            "postsynaptic": {
              "cell_types": [
                "B"
              ],
            },
            "affinity": 0.5,
            "contacts": {
              "distribution": "norm",
              "loc": 10,
              "scale": 2
            }
          }
        }

    .. code-block:: python

       config.connectivity.add(
         "A_to_B",
         strategy="bsb.connectivity.VoxelIntersection",
         presynaptic=dict(cell_types=["A"]),
         postsynaptic=dict(cell_types=["type_B"]),
         affinity= 0.5,
         contacts= dict(
           distribution="norm",loc=10,scale=2
         )
       )

In this case, the number of synapses is randomly drawn from a normal distribution
with a mean of 10 and a standard deviation of 2.

.. note::
  Normal distribution is just one option but all the distributions available in your scipy package
  can be used.
:class:`SegmentIntersection <bsb:bsb.connectivity.detailed.segment_intersection.SegmentIntersection>`
=====================================================================================================

This strategy connects cells whose morphology branches come within a given distance of
each other. Each branch segment is treated as a capsule, a line segment with a radius, and
an exact segment to segment distance test decides every contact. Unlike
:class:`VoxelIntersection <bsb:bsb.connectivity.detailed.voxel_intersection.VoxelIntersection>`,
which groups compartments into cubic voxels and so trades away morphological detail, this
strategy keeps the full spatial specificity of the traced morphology. Use it when that
detail matters and you have morphologies that justify it.

The geometric search runs in the ``bsb-native`` compiled kernel, so the strategy requires
that package (a dependency of ``bsb-core``, installed with it). It emits the same
``[cell, branch, point]`` location triples as
:class:`VoxelIntersection <bsb:bsb.connectivity.detailed.voxel_intersection.VoxelIntersection>`,
so the two are interchangeable.

* :guilabel:`contact_distance`: the distance, on top of the two segment radii, within which
  two segments form a contact. Must be positive; defaults to ``0``, meaning the capsules
  have to touch.
* :guilabel:`affinity`: a fraction between ``0`` and ``1`` giving the tendency of cells to
  connect to the partners they intersect with. Use it to downregulate how many cells any
  one cell connects to. Defaults to ``1``, which keeps every partner.
* :guilabel:`seed`: base seed for the :guilabel:`affinity` subsampling. It is combined with
  each cell's id, so a run reproduces regardless of how the network is chunked or how its
  jobs happen to be scheduled. Unused when :guilabel:`affinity` is ``1``.
* :guilabel:`favor_cache`: which side builds the segment trees, ``"pre"`` (default) or
  ``"post"``. The trees are cached per morphology, so favor the side with fewer unique
  morphologies.

.. tab-set-code::

    .. code-block:: json

        {
          "A_to_B": {
            "strategy": "bsb.connectivity.SegmentIntersection",
            "presynaptic": {
              "cell_types": [
                "A"
              ]
            },
            "postsynaptic": {
              "cell_types": [
                "B"
              ]
            },
            "contact_distance": 3.0,
            "affinity": 0.5,
            "seed": 42
          }
        }

    .. code-block:: python

      config.connectivity.add(
        "A_to_B",
        strategy="bsb.connectivity.SegmentIntersection",
        presynaptic=dict(cell_types=["A"]),
        postsynaptic=dict(cell_types=["B"]),
        contact_distance=3.0,
        affinity=0.5,
        seed=42,
      )

This connects cells of type A to cells of type B wherever their branches pass within
``3`` micrometers of each other, keeping half of the partners found, reproducibly.

.. note::
  :guilabel:`affinity` limits how many partner cells are kept, not how many contacts are
  formed with each partner. Every contact found between a kept pair is emitted.
