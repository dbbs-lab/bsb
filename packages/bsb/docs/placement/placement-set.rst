##############
Placement sets
##############

:class:`PlacementSets <bsb:bsb.storage.interfaces.PlacementSet>` are constructed from the
:class:`bsb:bsb.storage.Storage` and can be used to retrieve the positions, morphologies,
rotations and additional datasets.

.. note::

  Loading datasets from storage is an expensive operation. Store a local reference to the
  data you retrieve instead of making multiple calls.

Retrieving a PlacementSet
=========================

Multiple ``get_placement_set`` methods exist in several places as shortcuts to create the
same :class:`bsb:bsb.storage.interfaces.PlacementSet`. If the placement set does not exist, a
``DatesetNotFoundError`` is thrown.

.. code-block:: python

  from bsb import from_storage

  scaffold = from_storage("my_network.hdf5")
  ps = scaffold.get_placement_set("my_cell")
  # Alternatives to obtain the same placement set:
  ps = scaffold.get_placement_set(network.cell_types.my_cell)
  ps = scaffold.cell_types.my_cell.get_placement_set()

  print(ps.tag)  # Name of the placement set

Identifiers
===========

Cells have no global identifiers, instead you use the indices of their data, i.e. the
n-th position belongs to cell n, and so will the n-th rotation.
To easily retrieve the cells' IDs make use of the method :meth:`bsb:bsb.storage.interfaces.PlacementSet.load_ids`.

.. code-block:: python

    list_of_ids = ps.load_ids()


Positions
=========

The positions of the cells can be retrieved using the
:meth:`bsb:bsb.storage.interfaces.PlacementSet.load_positions` method.

.. code-block:: python

  for n, position in enumerate(ps.load_positions()):
    print(f"Cell {n}, position: {pos}")

Morphologies
============

The morphology of the cells can be retrieved using the
:meth:`bsb:bsb.storage.interfaces.PlacementSet.load_morphologies` method.

.. code-block:: python

  for n, (pos, morpho) in enumerate(zip(ps.load_positions(), ps.load_morphologies())):
    print(f"Cell {n}, position: {pos}, morpho: {morpho}")

.. warning::

   | Loading morphologies is especially expensive.
   | :meth:`bsb:bsb.storage.interfaces.PlacementSet.load_morphologies` returns a
     :class:`bsb:bsb.morphologies.MorphologySet`.
   | There are better ways to iterate over it using either **soft caching** or **hard caching**.

Rotations
=========

The positions of the cells can be retrieved using the
:meth:`bsb:bsb.storage.interfaces.PlacementSet.load_rotations` method.

.. code-block:: python

  for n, rotation in enumerate(ps.load_rotations()):
    print(f"Cell {n}, rotation: ", rotation)

Labeling
========

You can label cells and/or their attached morphologies using the
:meth:`bsb:bsb.storage.interfaces.PlacementSet.load_rotations`

Additional datasets
===================

Not implemented yet.
