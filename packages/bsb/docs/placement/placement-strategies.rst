############################
List of placement strategies
############################

:class:`RandomPlacement <bsb:bsb.placement.random.RandomPlacement>`
===================================================================

This class assigns a random position to each cell within their related partition. Below is an example with 10 cells.

.. tab-set-code::

    .. code-block:: json

        "cell_types": {
            "my_cell": {
                "spatial": {
                    "count": 10,
                    "radius": 5
                }
            }
        },

        "placement": {
            "place_randomly":{
                "strategy": "bsb.placement.particle.RandomPlacement",
                "partitions": ["my_layer"],
                "cell_types": ["my_cell"]
            }
        },

    .. code-block:: python

      config.cell_types.add(
        "my_cell",
        spatial=dict(radius=5, count=10)
      )
      config.placement.add(
        "place_randomly",
        strategy="bsb.placement.RandomPlacement",
        partitions=["my_layer"],
        cell_types=["my_cell"],
      )

.. note::
 This strategy will ensure that the cell somas (represented as sphere)
 do not occupy an excessive volume with respect to their containing partition.
 Therefore, the ratio of the total cell soma volume to the partition volume, referred as the `packing factor`,
 should not exceed 0.4.

:class:`ParallelArrayPlacement <bsb:bsb.placement.arrays.ParallelArrayPlacement>`
=================================================================================

This class places a single layer of cells on the `xy` plane in an aligned array fashion.
To this end, it create a lattice with fixed spacing between cell positions for each of its row (``spacing_x`` in µm).
The lattice can be additionally rotated along the `z` axis (``angle`` defined in degrees).

.. tab-set-code::

    .. code-block:: json

        "cell_types": {
            "my_cell": {
                "spatial": {
                    "count": 100,
                    "radius": 1
                }
            }
        },

        "placement": {
            "place_on_flat_array":{
                "strategy": "bsb.placement.ParallelArrayPlacement",
                "partitions": ["my_layer"],
                "cell_types": ["my_cell"],
                "spacing_x": 10,
                "angle": 0
            }
        },

    .. code-block:: python

      config.cell_types.add(
        "my_cell",
        spatial=dict(radius=1, count=100)
      )
      config.placement.add(
        "place_on_flat_array",
        strategy="bsb.placement.ParallelArrayPlacement",
        partitions=["my_layer"],
        cell_types=["my_cell"],
        spacing_x=10,
        angle=0
      )


:class:`FixedPositions <bsb:bsb.placement.strategy.FixedPositions>`
===================================================================

This class places the cells at fixed positions specified by the attribute ``positions``.

* ``positions``: a list of 3D points where the neurons should be placed. For example:

.. tab-set-code::

    .. code-block:: json

        "cell_types": {
            "my_cell": {
                "spatial": {
                    "count": 2,
                    "radius": 2
                }
            }
        },

        "placement": {
            "place_in_fixed_position":{
                "strategy": "bsb.placement.FixedPositions",
                "partitions": ["my_layer"],
                "cell_types": ["my_cell"],
                "positions": [[0, 0, 0], [20, 20, 20]]
            }
        },

    .. code-block:: python

      config.cell_types.add(
        "my_cell",
        spatial=dict(radius=2, count=2)
      )
      config.placement.add(
        "place_in_fixed_position",
        strategy="bsb.placement.FixedPositions",
        partitions=["my_layer"],
        cell_types=["my_cell"],
        positions=[[0, 0, 0], [20, 20, 20]]
      )

In this case, we place two cells of type ``my_cell`` at fixed positions
with coordinates [0, 0, 0] and [20, 20, 20].

.. _distrib_placement:

:class:`DistributionPlacement <bsb:bsb.placement.random.DistributionPlacement>`
===============================================================================

This class places cells whose coordinate along a given axis follows a `scipy` statistical
distribution. For each chunk of the partition, the distribution is sampled within the ratio
interval that the current chunk occupies along the axis inside the partition.
The two remaining axes are assigned uniformly at random within the chunk bounds.

* ``distribution``: a `scipy.stats` distribution node, specified by its ``distribution``
  name and any additional keyword arguments passed to the distribution constructor.
* ``axis``: the axis index (``0`` for *x*, ``1`` for *y*, ``2`` for *z*) along which
  to apply the distribution. Defaults to ``2`` (*z*).
* ``direction``: ``"positive"`` (default) or ``"negative"`` — whether to apply the
  distribution in the positive or negative direction along the axis.
* ``interval_probability``: tail probability used to clip the distribution to a finite
  interval (default ``1e-9``). Increase this to further restrict the sampling range.

Below is an example that places 100 cells following a normal distribution centred at the
middle of the layer along the *z*-axis (``loc=0.5``, ``scale=0.15``):

.. tab-set-code::

    .. code-block:: json

        "cell_types": {
            "my_cell": {
                "spatial": {
                    "count": 100,
                    "radius": 2
                }
            }
        },

        "placement": {
            "place_by_distribution": {
                "strategy": "bsb.placement.DistributionPlacement",
                "partitions": ["my_layer"],
                "cell_types": ["my_cell"],
                "distribution": {
                    "distribution": "norm",
                    "loc": 0.5,
                    "scale": 0.15
                },
                "axis": 2,
                "direction": "positive"
            }
        },

    .. code-block:: python

      config.cell_types.add(
        "my_cell",
        spatial=dict(radius=2, count=100)
      )
      config.placement.add(
        "place_by_distribution",
        strategy="bsb.placement.DistributionPlacement",
        partitions=["my_layer"],
        cell_types=["my_cell"],
        distribution=dict(distribution="norm", loc=0.5, scale=0.15),
        axis=2,
        direction="positive",
      )

.. note::
 The ``loc`` and ``scale`` parameters (and all other distribution parameters) are
 expressed in the same units as the distribution itself — they are **not** automatically
 normalised to the partition extent. The sampled values are mapped onto the partition
 via the ratio interval of the chunk, so choose distribution parameters accordingly.
 For instance, a ``norm`` with ``loc=0.5, scale=0.15`` concentrates cells near the
 centre of the partition with a spread of roughly ±15 % of the full layer height.
