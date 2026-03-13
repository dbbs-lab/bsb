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

Multiple ``get_placement_set`` methods exist in several places as shortcuts to access the
same :class:`PlacementSet<bsb:bsb.storage.interfaces.PlacementSet>` object.
If the placement set does not exist, a ``DatesetNotFoundError`` is thrown.

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
To easily retrieve the cells' IDs make use of the method :meth:`load_ids <bsb:bsb.storage.interfaces.PlacementSet.load_ids>`.

.. code-block:: python

    list_of_ids = ps.load_ids()


Positions
=========

The positions of the cells can be retrieved using the
:meth:`load_positions <bsb:bsb.storage.interfaces.PlacementSet.load_positions>` method.

.. code-block:: python

  for n, position in enumerate(ps.load_positions()):
    print(f"Cell {n}, position: {pos}")

Morphologies
============

The morphology of the cells can be retrieved using the
:meth:`load_morphologies <bsb:bsb.storage.interfaces.PlacementSet.load_morphologies>` method.

.. code-block:: python

  for n, (pos, morpho) in enumerate(zip(ps.load_positions(), ps.load_morphologies())):
    print(f"Cell {n}, position: {pos}, morpho: {morpho}")

.. warning::

   | Loading morphologies is especially expensive.
   | :meth:`load_morphologies <bsb:bsb.storage.interfaces.PlacementSet.load_morphologies>` returns a
     :class:`MorphologySet <bsb:bsb.morphologies.MorphologySet>`.
   | There are better ways to iterate over it using either **soft caching** or **hard caching**.

Rotations
=========

The positions of the cells can be retrieved using the
:meth:`load_rotations <bsb:bsb.storage.interfaces.PlacementSet.load_rotations>` method.

.. code-block:: python

  for n, rotation in enumerate(ps.load_rotations()):
    print(f"Cell {n}, rotation: ", rotation)

Chunk filtering
===============

You can use a list of Chunks to subsample the cells present within them.
This can be done when you generate the `PlacementSet` object with on of the function
``get_placement_set`` or using the
:meth:`set_chunk_filter <bsb:bsb.storage.interfaces.PlacementSet.set_chunk_filter>` method.

.. important::

    Note that the ids of the placement set will be remapped according to the Chunk filter

.. code-block:: python

    from bsb import Chunk

    # we suppose here a case where 10 `my_cell` cells are placed in two Chunks
    # 7 in the Chunk [0, 0, 0]
    # 3 in the Chunk [0, 0, 1]
    ps = scaffold.get_placement_set(
            "my_cell",
            chunks=[Chunk([0, 0, 0], chunk_size=100)]
    )
    print(ps.get_all_chunks())  # should print Chunk([0, 0, 0])
    print(ps.load_ids())  # should print [0, 1, 2, 3, 4, 5, 6]
    ps.set_chunk_filter([Chunk([0, 0, 1], chunk_size=100)])
    print(ps.get_all_chunks())  # should print Chunk([0, 0, 1])
    print(ps.load_ids())  # should print [0, 1, 2]
    ps.set_chunk_filter([])  # reset chunk filter
    print(ps.load_ids())  # should print [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

Labeling
========

You can label cells using the
:meth:`label <bsb:bsb.storage.interfaces.PlacementSet.label>` or the
:meth:`label_by_mask <bsb:bsb.storage.interfaces.PlacementSet.label_by_mask>` methods.
These functions are almost identical. The first one uses cell ids while the other needs a boolean mask array.

.. note::

    Labeling is cumulative, i.e., if you relabel a cell then the new labels will be
    added to the previous ones. You can remove labels previously put, using the
    :meth:`remove_labels <bsb:bsb.storage.interfaces.PlacementSet.remove_labels>` or
    :meth:`remove_labels_by_mask <bsb:bsb.storage.interfaces.PlacementSet.remove_labels_by_mask>` functions.

.. code-block:: python

  # Assuming ps has 7 cells
  print(ps.load_ids())  # prints [0, 1, 2, 3, 4, 5, 6]
  # you can put as many labels onto one cell
  ps.label(["labelA", "labelB"], [1, 5, 6])
  # the boolean mask array should be the same size as the ps
  ps.label_by_mask(["labelC"], [True, True, False, True, False, True, False])
  # we overwrite the previous labels
  ps.remove_labels(["labelA", "labelB", "labelC"], [1])
  ps.label(["labelD"], [1])

You can retrieve the cells labelled leveraging the
:meth:`get_labelled <bsb:bsb.storage.interfaces.PlacementSet.get_labelled>` or the
:meth:`get_label_mask <bsb:bsb.storage.interfaces.PlacementSet.get_label_mask>` methods.
These functions are the counterpart of the ``label`` and ``label_by_mask`` functions:
one returns the list of ids labelled while the other provides a boolean mask array.
Finally, you can retrieve the list of unique label sets that is attached to each cell with the
method :meth:`get_unique_labels <bsb:bsb.storage.interfaces.PlacementSet.get_unique_labels>` .

.. note::

    If you provide `None` as labels to these functions, they would return all ps ids.
    You should provide an empty list to filter non labelled cells.

.. note::

    The function will return cells labelled by **any** of the labels provided.

.. code-block:: python

    # reusing previous example
    print(ps.get_labelled(["labelA"]))  # should print [5, 6]
    print(ps.get_label_mask(["labelC"]))  # should print [True, False, False, True, False, True, False]
    print(ps.get_labelled(["labelB", "labelC"])) # should print [0, 3, 5, 6]
    print(ps.get_labelled(["labelD"]))  # should print [1]
    print(ps.get_label_mask())  # should print [True, True, True, True, True, True, True]
    print(ps.get_labelled([]))  # should print [2, 4]
    # should print [set(), {"labelA", "labelB"}, {"labelC"}, {"labelA", "labelB", "labelC"}, {"labelD"}]
    print(ps.get_unique_labels())

You can also filter your `PlacementSet` according to the labels used setting the `label_filter`s
(getter: :meth:`get_label_filter <bsb:bsb.storage.interfaces.PlacementSet.get_label_filter>`
setter: :meth:`set_label_filter <bsb:bsb.storage.interfaces.PlacementSet.set_label_filter>`).
This means that the length of the `PlacementSet` and all its attached datasets
(ids, rotations, morphologies) will be sub-sampled according to the label filter.

Similar to the previous function, this filter returns cells matching any of the labels provided.

.. important::

    Unlike the Chunk filtering, the PlacementSet ids do not change with the labels filter.

.. note::

    You can also filter cell labels when you retrieve the `PlacementSet`
    with the function ``get_placement_set``.

.. code-block:: python

    # reusing previous example
    ps.set_label_filter(["labelA"])
    print(ps.load_ids())  # should print [5, 6]
    print(len(ps))  # should print 2
    ps.set_label_filter(["labelB", "labelC"])
    print(ps.load_ids())  # should print [0, 3, 5, 6]
    ps.set_label_filter([])  # filter cells that are not labelled
    print(ps.load_ids()) # should print [2, 4]
    ps.set_label_filter(None)  # reset label filtering
    print(ps.load_ids()) # should print [0, 1, 2, 3, 4, 5, 6]


.. important::
    If you want to label the PlacementSet again after filtering it,
    you have to use indexes corresponding to its new length.

.. code-block:: python

    # reusing previous example
    ps.set_label_filter(["labelA"])
    print(ps.load_ids())  # should print [5, 6]
    # So to label cell 6, we use its new index: 1
    ps.label(["labelE"], [1])  # will add label "labelE" to cell 6
    print(ps.get_labelled(["labelE"]))  # should print [6]

Morphology filtering
====================

Similar to the general cell labelling, you can use morphology labels
(ie. labels assigned to morphology points, see also
:ref:`this page <morphology_labels>`) to filter the morphologies sections
that you want to isolate in your ps.

.. note::

    You can also filter morphology labels when you retrieve the `PlacementSet`
    with the function ``get_placement_set``.

.. code-block:: python

    ps.set_morphology_label_filter(["dendrites", "apical_dendrites"])

Additional datasets
===================

Not implemented yet.
