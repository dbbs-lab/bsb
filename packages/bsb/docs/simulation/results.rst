==================
Simulation results
==================

A simulation writes its results as a `Neo <https://neo.readthedocs.io>`_ block,
stored in a NixIO file. One run produces one file, whatever it took to make it:
under MPI each rank writes its own part and rank 0 merges them, but that is an
implementation detail of the run, not something a reader has to know about.

Recordings are per target
=========================

Every recording belongs to a single target: one cell, one point on a cell, one
synapse. A device that watches a thousand cells writes a thousand recordings, not
one recording holding a thousand cells' data.

This costs nothing that matters and buys the thing that does: a recording can be
annotated with exactly what it recorded. A spike train of the whole population can
only say which cells are in it; a spike train per cell can also say which cell, of
which cell model, and carry any annotation a device or a downstream tool wants to
add. Neuroscience is numerous by design, and the tools downstream of Neo are built
to handle many objects.

A device writes one recording per target it watched, and a target that produced
nothing gets an empty one. Its recordings are therefore its targets, which is what
makes a population answerable from the results alone: a cell with an empty train
was watched and stayed quiet, a cell with no train at all was never watched.

Annotations
===========

All annotations the BSB writes are prefixed with ``bsb_``, so they never collide
with the annotations of Neo or of other tools. What a signal measures is described
by Neo itself, through the signal's ``name`` (such as ``spikes``, ``v`` or ``i``) and
its units.

Every recording
---------------

Every recording carries these annotations, whichever backend produced it and
whichever Neo container it lands in:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Annotation
     - Meaning
   * - ``bsb_device_name``
     - Name of the device that made the recording.
   * - ``bsb_device_kind``
     - The kind of device, as configured, such as ``spike_recorder``.
   * - ``bsb_simulation_id``
     - Identity of the run, the same as in the block's provenance.
   * - ``bsb_segment_id``
     - Identity of the segment the recording belongs to.
   * - ``bsb_recording_kind``
     - What kind of target was recorded: ``cell``, ``point``, ``synapse`` or
       ``device``. It decides which annotations below address the target.
   * - ``bsb_direction``
     - ``record`` when the device observed the target, ``stimulate`` when the
       recording is what the device injected into it.

The first four are stamped by the :class:`~bsb.simulation.results.SimulationResult`
rather than by each device, so a new backend cannot forget to say where a signal
came from. A device that sets one of them itself keeps its own answer.

The result enforces the rest. A recorder has to belong to a device, and at every
checkpoint anything a recorder recorded without one of the recording kinds, or
without a direction of ``record`` or ``stimulate``, is not written: it is dropped
with a :class:`~bsb.exceptions.ResultsWarning` that names the device. The kinds are
a closed set, so every recording in a file can be traced back to what it recorded.

Per kind of target
------------------

A target is addressed in the network's own terms: a cell by its placement set and
its id in it, a location by the branch and point of the cell's morphology. A
simulator's own identifiers, such as NEST node ids, arbor gids or NEURON sections,
are never written: they mean nothing outside the run that assigned them.

.. list-table::
   :header-rows: 1
   :widths: 15 40 45

   * - Kind
     - Annotations
     - Addresses
   * - ``cell``
     - ``bsb_ps_name``, ``bsb_cell_model``, ``bsb_cell_id``
     - A whole cell: the placement set it is in, the cell model it was simulated
       with, and its id in the placement set.
   * - ``point``
     - The ``cell`` annotations, and ``bsb_branch``, ``bsb_point``, ``bsb_arc``
     - A location on a cell's morphology: the branch, the point on the branch, and
       where along the branch, as a fraction of its length.
   * - ``synapse``
     - The ``point`` annotations, and ``bsb_synapse_type``; ``bsb_pre_ps_name``,
       ``bsb_pre_cell_model`` and ``bsb_pre_cell_id`` when the synapse belongs to a
       connection
     - A synapse on a cell, and the presynaptic cell it receives from.
   * - ``device``
     - None
     - Nothing in the network: a signal the device computes itself, rather than one
       it takes from a cell.

The devices that come with the BSB write:

.. list-table::
   :header-rows: 1
   :widths: 50 25 25

   * - Device
     - Kind
     - Direction
   * - NEST ``spike_recorder`` and ``multimeter``, arbor ``spike_recorder``
     - ``cell``
     - ``record``
   * - NEURON ``voltage_recorder``
     - ``point``
     - ``record``
   * - NEURON ``current_clamp`` and ``vclamp``
     - ``point``
     - ``stimulate``
   * - NEURON ``synapse_recorder``
     - ``synapse``
     - ``record``

A device author builds these annotations with
:func:`~bsb.simulation.results.cell_annotations`,
:func:`~bsb.simulation.results.point_annotations`,
:func:`~bsb.simulation.results.synapse_annotations` and
:func:`~bsb.simulation.results.device_annotations`, and passes them to the Neo
object:

.. code-block:: python

    from bsb import cell_annotations

    SpikeTrain(
        times,
        units="ms",
        t_stop=duration,
        name="spikes",
        **cell_annotations(cell_model, cell_id, "record"),
    )

Reading results
===============

A recording names what it recorded, but only the network can say where that is or
what it belongs to. :func:`~bsb.simulation.results.read_results` reads a results
file together with the network it was simulated on:

.. code-block:: python

    from bsb import read_results

    results = read_results("network.hdf5", "simulation-results/run.nio")
    for recording in results.recordings("my_spike_recorder"):
        print(recording.target.id, recording.target.position, len(recording.signal))

Each recording has a ``kind``, a ``direction``, and a ``target``: what it recorded,
in the network. The target depends on the kind:

.. list-table::
   :header-rows: 1
   :widths: 15 30 55

   * - Kind
     - Target
     - Offers
   * - ``cell``
     - :class:`~bsb.simulation.results.RecordedCell`
     - ``id``, the cell ``model``, the network's ``cell_type`` and
       ``placement_set``, and the cell's ``position``, ``morphology`` and
       ``rotation``.
   * - ``point``
     - :class:`~bsb.simulation.results.RecordedPoint`
     - The ``cell`` it is on, ``branch``, ``point`` and ``arc``, and its
       ``position`` in the network.
   * - ``synapse``
     - :class:`~bsb.simulation.results.RecordedSynapse`
     - The ``cell`` it is on, ``branch``, ``point``, ``arc``, its ``position`` in
       the network, ``synapse_type``, and the ``presynaptic`` cell, if any.
   * - ``device``
     - :class:`~bsb.simulation.results.RecordedDevice`
     - The device's ``name``, its ``kind``, and its ``configuration`` as the
       simulation ran with it.

A cell's ``morphology`` is that cell's morphology as it is in the network: rotated
by the cell's ``rotation`` and moved to its ``position``. It is a copy, so changing it
changes nothing in the network. The ``position`` of a point or a synapse is where it
is on that morphology. Morphologies and rotations are loaded from the network once per
placement set, and only when a recording asks for them.

A recording of a kind this version of the BSB does not know, such as one in a file
written by a newer version, still reads, with ``target`` set to ``None``; its
annotations stay available as ``recording.annotations``.
``results.recordings(kind="synapse")`` selects recordings by kind.

The reader also offers:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Attribute
     - Meaning
   * - ``network``
     - The network, as a :class:`~bsb.core.Scaffold`.
   * - ``runs``
     - The runs in the file, as :class:`~bsb.simulation.results.SimulationRun`
       objects.
   * - ``devices``
     - The names of the devices that recorded, across the runs.
   * - ``simulation``
     - The network's simulation of the same name, or ``None`` if it has none.
   * - ``configuration``
     - The configuration tree of the simulation, as it ran.
   * - ``provenance``
     - The provenance of the run: seed, duration, resolution, and more.

Pass either a path or a network that is already open.

A file can hold several runs, of different simulations or of the same one. Each run
carries its own configuration and provenance, so all of them are read and traced
back to the network without choosing one first. ``results.recordings()`` yields the
recordings of every run, and each recording's ``run`` says which one made it. A run
offers ``name``, ``run_index``, ``simulation``, ``configuration``, ``provenance``,
``devices`` and ``recordings()`` of its own. ``simulation``, ``configuration`` and
``provenance`` belong to one run, so on the reader they are only available when the
file holds a single run.

Before anything is returned, every run is verified against the network using its
provenance:

* Results of another network raise a
  :class:`~bsb.exceptions.ResultsMismatchError`. Analysed against the wrong network,
  they would give plausible nonsense.
* A network that was written to after the run emits a
  :class:`~bsb.exceptions.ResultsWarning`: positions or labels may have changed
  since. Opening a network is not writing to it.
* A run that recorded no network identity also warns, since the pair cannot be
  verified.

The results file does not say where its network is. Paths move, and a stored path
would leak local directories into shared files, so the caller passes both.

Reading a bare results file
---------------------------

Without the network, :func:`~bsb.simulation.results.iter_recordings` walks the
recordings of a block, a segment, or a list of either, and yields a
:class:`~bsb.simulation.results.Recording` for each: the device, the kind, the
direction, the Neo object, and its annotations. It takes the containers Neo keeps
separate (spike trains, analog signals) and presents them as one sequence, so
reading does not depend on which kind of device made the data.

.. code-block:: python

    from bsb.simulation.results import iter_recordings

    # every recording of one device
    for recording in iter_recordings(block, device="spikes_exc"):
        print(recording.annotations["bsb_cell_id"], len(recording.signal))

    # everything recorded on one cell, across devices
    for recording in iter_recordings(block, cell_model="granule_cell", cell_id=42):
        print(recording.device, recording.kind, recording.signal)

To count a population's spikes, sum the trains of its device:

.. code-block:: python

    recordings = list(iter_recordings(block, device="spikes_exc"))
    n_spikes = sum(len(recording.signal) for recording in recordings)
    rate = n_spikes / duration * 1000.0 / len(recordings)

Provenance
==========

Alongside the results, the block records what produced them:
:func:`~bsb.simulation.results.read_simulation_config` returns the configuration
of the simulation that ran, and
:func:`~bsb.simulation.results.read_provenance` returns the run's provenance. Both
read a block, whether it came from a
:class:`~bsb.simulation.results.SimulationResult` or from a file.
