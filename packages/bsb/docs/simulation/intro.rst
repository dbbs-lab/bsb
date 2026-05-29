###################
Simulating Networks
###################

The BSB offers adapters that enable you to simulate
your network using widely-used neural simulation software. Consequently, once the model is created,
it can be simulated across different software platforms without requiring modifications or adjustments.
Currently, adapters are available for NEST, NEURON, and ARBOR,
although support for ARBOR is not yet fully developed.

All simulation details are specified within the simulation block, which includes:
 * a ``simulator`` : the software chosen for the simulations.
 * set of ``cell models`` : the simulator specific representations of the network's :doc:`CellTypes </cells/intro>`
 * set of ``connection models`` :  that instruct the simulator on how to handle the :doc:`ConnectivityStrategies </connectivity/defining>` of the network
 * set of ``devices`` : define the experimental setup (such as input stimuli and recorders).

All of the above is simulation backend specific and is covered in the corresponding sections:

 * :doc:`NEST </simulation/nest>`.
 * :doc:`NEURON </simulation/neuron>`.
 * :doc:`ARBOR </simulation/arbor>`.

Running Simulations
===================

Simulations can be run through the CLI or through the ``bsb`` library for more
control:

.. tab-set-code::

    .. code-block:: bash

      bsb simulate my_network.hdf5 my_sim_name

    .. code-block:: python

        from bsb import from_storage
        network = from_storage("my_network.hdf5")
        network.run_simulation("my_sim")

When using the CLI, the framework sets up a "hands off" simulation workflow:

* Read the network file
* Read the simulation configuration
* Translate the simulation configuration to the simulator
* Create all cells, connections and devices
* Run the simulation
* Collect all the output

When you use the library, you can set up more complex workflows, such as
:doc:`parameter sweeps </examples/nest_repeated_sim>`

.. rubric:: Parallel simulations

To parallelize any BSB task prepend the MPI command in front of the BSB CLI command, or
the Python script command:

.. code-block:: bash

  mpirun -n 4 bsb simulate my_network.hdf5 my_sim_name
  mpirun -n 4 python my_simulation_script.py

Where ``n`` is the number of parallel nodes you'd like to use.

Targetting
==========

To customize our experimental setup, devices can be arranged to target specific cell populations.
In the BSB, several methods are available to filter the populations of interest.
These methods can be based on various criteria, including cell characteristics,
labels, and geometric constraints within the network volume.

The target population can be defined when a device block is created in the configuration:

.. tab-set-code::

    .. code-block:: json

        "my_new_device": {
          "device": "device_type",
          "targetting": {
            "strategy": "my_target_strategy",
          }
        }
    .. code-block:: python

        config.simulations["my_simulation_name"].devices=dict(
          my_new_device={
            "device": "device_type",
            "targetting": {
              "strategy": "my_target_strategy",
            }
          }
        )

Strategies based on cell
------------------------

``strategy name``: :guilabel:`all` . This is a basic strategy that targets all the cells in our network

Target by cell model
^^^^^^^^^^^^^^^^^^^^

``strategy name``: :guilabel:`cell_model` . This strategy targets only the cells of the specified models.
Users must provide a list of cell models to target using the attribute :guilabel:`cell_models` .

Target by id
^^^^^^^^^^^^

``strategy name``: :guilabel:`by_id` . Each cell model is assigned a numerical identifier
that can be used to select the target cells.
It is necessary to provide a list of integers representing the cell IDs with the attribute :guilabel:`ids` :

* ``ids``: A *dict* that associates a cell model to a list of its neuron indexes to select.

Example selecting cells with IDs 2, 4, or 6 from ``my_cell_model``:

.. tab-set-code::

    .. code-block:: json

        "my_new_device": {
          "device": "device_type",
          "targetting": {
            "strategy": "by_id",
            "ids": {"my_cell_model": [ 2, 4,6]}
          }
        }
    .. code-block:: python

        config.simulations["my_simulation_name"].devices=dict(
          my_new_device={
            "device": "device_type",
            "targetting": {
              "strategy": "by_id",
              "ids": {"my_cell_model": [ 2, 4,6]}
            }
          }
        )

Target by cell labels
^^^^^^^^^^^^^^^^^^^^^

You can assign specific labels to subgroups of cells and use these labels to customize the targeting
behavior of your devices.
The strategy named :guilabel:`by_label` allows users to define which subgroups to target
using the :guilabel:`labels` attribute:

* ``labels``: A *list* of *str* specifying the labels corresponding to the subgroups to target.

Optionally, the :guilabel:`cell_models` attribute can still be used to further restrict the selection to specific cell models.

.. note::
  To learn how to assign labels to cells, see the :doc:`example </examples/label_cells>` provided.

Geometric strategies
--------------------

Instead of targeting cells based on characteristics or labels,
it is possible to target a defined region using geometric constraints.

Target a Cylinder
^^^^^^^^^^^^^^^^^

``strategy name``: :guilabel:`cylinder`. This strategy targets all the cells contained within a cylinder along the defined axis.
The user must provide three attributes:

* ``origin``: A *list* of coordinates representing the base of the cylinder for each non-main axis.
* ``axis``: A character is used to specify the main axis of the cylinder. Accepted values are "x," "y," and "z," with the default set to "y."
* ``radius``: A *float* representing the radius of the cylinder.

Target a Sphere
^^^^^^^^^^^^^^^

``strategy name``: :guilabel:`sphere`. This strategy targets all the cells contained within a sphere.
The user must provide two attributes:

* ``origin``: A *list* of *float* that defines the center of the sphere.
* ``radius``: A *float* representing the radius of the sphere.

Fraction Filter
---------------
All previous targeting strategies include a filtering mechanism to select a subset of cells
from the overall population.
Filtering can be based on either a fixed number of cells or a specified fraction of the total.

The following attributes can be added to the configuration to define the filtering criteria:

* ``count``: *int*, Specifies the exact number of cells to target.
* ``fraction``: *float*, Specifies the fraction of the total cell population to target.

Simulation results
==================

The results of a simulation are stored in ``.nio`` files, read and written via the
:doc:`Neo Python package <neo:index>` on top of an HDF5 container. Each file holds
one :class:`neo:neo.core.Block` containing one or more :class:`neo:neo.core.Segment`
objects (one per
:meth:`flush <bsb:bsb.simulation.results.SimulationResult.flush>`, typically one per
simulation run, more if checkpoints are emitted). Each segment carries the
:class:`neo:neo.core.SpikeTrain` and :class:`neo:neo.core.AnalogSignal` objects
produced by every recorder that ran during that flush.

The easiest entry point is the reader helper:

.. code-block:: python

   from bsb import read_nio, iter_recordings

   block = read_nio("output.nio")
   for rec in iter_recordings(block):
       # rec.kind is neo.SpikeTrain or neo.AnalogSignal
       # rec.ps_name, rec.cell_id, rec.device, rec.name, rec.units, rec.data, rec.annotations
       ...

:func:`iter_recordings <bsb:bsb.simulation.results.iter_recordings>` skips any Neo
object that does not carry a ``bsb_ps_name`` annotation (e.g. output from
third-party plugin devices that opted out of the convention). See the
:ref:`recorder convention <recorder-convention>` below. The yielded record is a
:class:`Recording <bsb:bsb.simulation.results.Recording>`;
:func:`read_nio <bsb:bsb.simulation.results.read_nio>` opens and returns the
underlying :class:`neo:neo.core.Block`.

Block-level provenance
----------------------

Every simulation result :class:`neo:neo.core.Block` carries a ``bsb_provenance``
annotation: a single dict recording who, where and when produced the file, and
which reconstruction it was run against.

.. code-block:: python

   prov = block.annotations["bsb_provenance"]
   prov["simulation_id"]                  # UUID4 for this run
   prov["scaffold"]["storage_id"]         # back-pointer to the reconstruction file
   prov["scaffold"]["state_id"]           # revision of that reconstruction at run time
   prov["simulator"]                      # {"name": "nest"|"neuron"|"arbor", "version": ..., "extra": {...}}
   prov["plugins"]                        # {category: {entry_name: {package, version}}}
   prov["seed"], prov["duration_ms"], prov["resolution_ms"]
   prov["started_at"], prov["finished_at"], prov["wall_seconds"]
   prov["host"]                           # platform, hostname, user, python_version, cwd
   prov["mpi_size"]

Each :class:`neo:neo.core.Segment` additionally carries ``segment_id`` (UUID4),
``checkpoint_index``, ``t_start_ms`` and ``t_stop_ms`` in its own annotations.

.. _recorder-convention:

The recorder annotation convention
----------------------------------

The BSB does **not** validate or constrain what recorders emit. A recorder is free
to add as many (or as few) Neo objects to a segment as it wants, of either kind, in
any shape it likes. The convention only describes what each emitted object's
``bsb_*`` annotations *assert*, in two layers: a **baseline** every recorder shares,
and a **target-kind** layer chosen by what is being recorded.

Baseline (every recorder)
^^^^^^^^^^^^^^^^^^^^^^^^^^

These annotations are present on every recorded object, regardless of what it
records:

``bsb_device_name`` (str), ``bsb_device_kind`` (str)
    The **device** that emitted the object: its configured name and its
    ``classmap_entry`` (``"spike_recorder"``, ``"multimeter"``, ``"voltage_recorder"``,
    …). Two devices recording the same target produce objects distinguishable by
    these keys.

``bsb_target_kind`` (str)
    What *kind of thing* the object records: ``"cell"``, ``"compartment"``,
    ``"synapse"``, ``"lfp"``, … This discriminator tells a consumer which
    target-kind fields (below) to expect.

``bsb_simulation_id`` (str), ``bsb_segment_id`` (str)
    Mirrors of the :class:`neo:neo.core.Block`- and :class:`neo:neo.core.Segment`-
    level UUIDs, denormalised onto each object so individual Neo objects stay
    self-identifying when extracted from the Block.

Neo's native fields carry *what quantity* is recorded: ``obj.name`` is the label
(e.g. ``"V_m"``, ``"I_syn"``; conventionally blank for a
:class:`neo:neo.core.SpikeTrain`) and ``obj.units`` the dimension (a ``quantities``
unit, e.g. ``mV``, ``nA``).

Target kinds (proposed)
^^^^^^^^^^^^^^^^^^^^^^^

On top of the baseline, each ``bsb_target_kind`` declares further fields that locate
its target. These are first-class flat ``bsb_*`` annotations, siblings of the
baseline keys (not nested in a blob), so a consumer reads ``rec.annotations`` keys
directly. This taxonomy is part of the proposal; the field sets per kind are open to
feedback and new kinds can be added.

``"cell"``
    A whole cell (e.g. a point-neuron spike train or membrane voltage). Adds
    ``bsb_ps_name`` (str), ``bsb_cell_id`` (int), ``bsb_cell_model`` (str): which
    placement set, the cell's index within it, and the cell model it was wired as.
    The placement-set name is the BSB identity; the BSB does not use
    simulator-internal GIDs in its data model.

``"compartment"``
    A location on a cell's morphology. Adds the ``"cell"`` fields plus the site:
    ``bsb_section`` (str) and ``bsb_arc`` (float in ``[0, 1]``), and optionally
    ``bsb_compartment_index`` (int).

``"synapse"``
    A synapse on a postsynaptic cell. Adds the postsynaptic ``"cell"`` fields, the
    site on that cell (``bsb_section`` / ``bsb_arc``), ``bsb_synapse_type`` (str),
    and the presynaptic identity (proposed: ``bsb_pre_ps_name`` /
    ``bsb_pre_cell_id``).

``"lfp"``
    A local field potential over a region, not tied to a single cell. Declares the
    recording electrode / probe identity and its position (proposed: ``bsb_probe`` /
    ``bsb_position``).

The built-in recorders cover three kinds: NEST ``spike_recorder`` / ``multimeter``
and Arbor ``spike_recorder`` emit ``"cell"``; NEURON ``voltage_recorder`` (and
``current_clamp``) emit ``"compartment"``; NEURON ``synapse_recorder`` emits
``"synapse"``. The ``"lfp"`` kind has no built-in recorder yet.

Examples
^^^^^^^^

All spikes from cell 17 of placement set ``pc``:

.. code-block:: python

   import neo
   from bsb import iter_recordings, read_nio

   block = read_nio("output.nio")
   for rec in iter_recordings(block):
       if rec.kind is neo.SpikeTrain and rec.ps_name == "pc" and rec.cell_id == 17:
           print(rec.data)

All membrane voltage traces from a specific device, grouped by cell:

.. code-block:: python

   from collections import defaultdict

   per_cell = defaultdict(list)
   for rec in iter_recordings(block):
       if rec.kind is neo.AnalogSignal and rec.device == "v_recorder_pc" and rec.name == "V_m":
           per_cell[rec.cell_id].append(rec)

All synaptic currents on the soma of any cell (filtering on the flat
``"synapse"``-kind fields):

.. code-block:: python

   for rec in iter_recordings(block):
       if (
           rec.annotations.get("bsb_target_kind") == "synapse"
           and rec.annotations.get("bsb_section") == "soma"
       ):
           ...

Writing custom recorders
^^^^^^^^^^^^^^^^^^^^^^^^

Custom recorder devices may follow the convention by setting the ``bsb_*``
annotations explicitly (easiest via the
:meth:`SimulationResult.spike_train
<bsb:bsb.simulation.results.SimulationResult.spike_train>` and
:meth:`SimulationResult.analog_signal
<bsb:bsb.simulation.results.SimulationResult.analog_signal>` convenience
constructors on
:attr:`simdata.result <bsb:bsb.simulation.adapter.SimulationData.result>`), or
ignore the convention entirely. Non-compliant objects still flow through and land
in the file;
:func:`iter_recordings <bsb:bsb.simulation.results.iter_recordings>` just skips
them.

Advanced Features
=================
There are other features of the simulation block that can be explored:

* :doc:`Controllers </simulation/simulation-controllers>`