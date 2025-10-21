How to label neurons
********************

After placing cells inside the scaffold model, it is possible to define postprocessing
functions that modify some features of the scaffold. For instance, it is possible to
define a function that, given a specific cell type, assigns a label to each cell belonging
to that cell type  (e.g., subdivide a certain population into different subpopulations
according to their position in the 3D space.)

Postprocessing functions can be configured in the :guilabel:`after_placement` dictionary
of the root node of the configuration file, specifying each postprocessing function with its
name, e.g. :guilabel:`Labels`:

.. tab-set-code::

  .. literalinclude:: /../../../examples/cell-labeling/configs/cell_labeling.json
    :language: json
    :lines: 40-45

  .. literalinclude:: /../../../examples/cell-labeling/configs/cell_labeling.yaml
    :language: yaml
    :lines: 31-34

  .. literalinclude:: /../../../examples/cell-labeling/scripts/cell_labeling.py
    :language: python
    :lines: 35-39

Here, we are linking the class ``LabelCellA`` stored in the file ``cell_labeling/label_cells.py``.
For more information on linking your Python classes to the configuration file see
:doc:`this section </config/nodes>`.

Example of a Python class for labeling neurons
----------------------------------------------

.. literalinclude:: /../../../examples/cell-labeling/cell_labeling/label_cells.py
  :language: python
  :lines: 2-

In this example, we can see that the ``LabelCellA`` class must inherit from
``AfterPlacementHook`` and it must specify a method ``postprocess`` in which the
neural population ``cell_A`` is subdivided into two populations.

Here, along the chosen axis, cells placed above the mean position of the population
will be assigned the label ``cell_A_type_1`` and the rest ``cell_A_type_2``.

You can then filter back these cells like so:

.. literalinclude:: /../../../examples/cell-labeling/scripts/test_labels.py
  :language: python

Full example configuration file
-------------------------------

.. tab-set-code::

  .. literalinclude:: /../../../examples/cell-labeling/configs/cell_labeling.json
    :language: json

  .. literalinclude:: /../../../examples/cell-labeling/configs/cell_labeling.yaml
    :language: yaml

  .. literalinclude:: /../../../examples/cell-labeling/scripts/cell_labeling.py
    :language: python