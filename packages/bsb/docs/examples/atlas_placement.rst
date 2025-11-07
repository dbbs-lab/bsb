Mouse brain atlas placement
===========================

The BSB supports integration with atlases. All that's required is to implement a
:class:`~bsb.topology.partition.Voxels` partition so that the atlas data can be converted
from the atlas raster format, into a framework object. The framework has the
:ref:`allen-atlas-integration` out of the box, and this example will use the
:class:`~bsb.topology.partition.AllenStructure` partition to showcase its usages.

After loading the brain region shapes from the atlas, we will use a local data file
to assign density values to each voxel, and place cells accordingly.

Topology
--------

We start by defining the topology: a region, and an ``allen`` partition:

.. literalinclude:: /../../../examples/atlas-modeling/configs/allen_structure.json
  :language: json
  :lines: 20-25,29-30
  :emphasize-lines: 6-7

BSB will here download the 2017 version of the CCFv3 mouse brain annotation atlas volume
from the Allen Institute website to define the shape of the partition.
Use :guilabel:`mask_source` to provide your own nrrd annotation volume file.

The :guilabel:`struct_name` refers to the Allen mouse brain region acronym or name.
You can also replace that with :guilabel:`struct_id`, if you are using the numeric identifiers.
You can find the ids, acronyms and names in the
`Allen Brain Atlas brain region hierarchy file <https://api.brain-map.org/api/v2/structure_graph_download/1.json>`_.


Cell types
----------

We now add a cell population ``my_cell`` in the ``declive``, it will be placed with a fixed
density of ``0.003/μm^3``:

.. literalinclude:: /../../../examples/atlas-modeling/configs/allen_structure.json
  :language: json
  :lines: 32-38,45-50,52-55

Cell Density files
------------------

Now in case we know the cell densities distribution inside the ``declive``, we can store it
inside a nrrd file and link it to the partition and cell population.
Here, we add a ``my_cell_density.nrrd`` file to the ``declive`` partition using the
:guilabel:`sources` attribute and finally to a cell population ``my_other_cell`` using the
:guilabel:`density_key` attribute:

.. literalinclude:: /../../../examples/atlas-modeling/configs/allen_structure.json
  :language: json
  :lines: 23-26,15-18,28-32,39-49,51-55
  :emphasize-lines: 4,7,17

Note that here the reference to the file ``data/my_cell_density.nrrd`` in ``my_other_cell``
is the name of the file without the extension (similar to the morphologies).

The :guilabel:`sources` file(s) will be loaded during the placement, and the values at the
coordinates of the voxels that make up our partition will be used to compute the number of
cells.

Finally, let us imagine we need to define 2 partitions, corresponding to 2 regions of the mouse
brain and place our two cell populations in both, then the simplest solution would be to declare
our density file in each partition. However, this solution will add the file to the ``Storage``
twice.

Hence, we **strongly** recommend you to declare any file that might be reused at different steps
of the reconstruction in the ``files`` root component (see also :ref:`this section <cfg_files>`).

.. literalinclude:: /../../../examples/atlas-modeling/configs/allen_structure.json
  :language: json
  :lines: 13-19,23-32,39-45
  :emphasize-lines: 1-2,12,21

Final configuration file
------------------------

.. literalinclude:: /../../../examples/atlas-modeling/configs/allen_structure.json
  :language: json