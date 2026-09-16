==================
Simulation results
==================

A simulation writes its results as a `Neo <https://neo.readthedocs.io>`_ block,
stored in a NixIO file. One run produces one file, whatever it took to make it:
under MPI each rank writes its own part and rank 0 merges them, but that is an
implementation detail of the run, not something a reader has to know about.

Recordings are per cell
=======================

Every recording belongs to a single cell. A device that watches a thousand cells
writes a thousand recordings, not one recording holding a thousand cells' data.

This costs nothing that matters and buys the thing that does: a recording can be
annotated with the cell it came from. A spike train of the whole population can
only say which cells are in it; a spike train per cell can also carry that cell's
model, and any per-cell annotation a device or a downstream tool wants to add.
Neuroscience is numerous by design, and the tools downstream of Neo are built to
handle many objects.

A device writes one recording per cell it watched, and a cell that produced
nothing gets an empty one. Its recordings are therefore its cells, which is what
makes a population answerable from the results alone: a cell with an empty train
was watched and stayed quiet, a cell with no train at all was never watched.

Nothing has to say which cells a device watched, because the recordings already
do. A population rate is the spikes summed over the number of recordings, and a
raster has a row for every cell whether or not it fired, rather than closing up
around the ones that did.

Annotations
===========

Every recording carries the same annotations, whichever backend produced it and
whichever Neo container it lands in:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Annotation
     - Meaning
   * - ``device``
     - Name of the device that made the recording.
   * - ``cell_model``
     - Name of the simulation's cell model that the cell belongs to. Absent for a
       device level record, such as a generator's own spikes.
   * - ``cell_id``
     - Id of the cell in the placement set of that cell model's cell type. Absent
       for a device level record.

Together, ``cell_model`` and ``cell_id`` address one row of the network, on every
backend:

.. code-block:: python

    cell_type = simulation.cell_models[cell_model].cell_type
    position = cell_type.get_placement_set().load_positions()[cell_id]

A simulator's own identifiers, such as NEST node ids or arbor gids, are never
written: they mean nothing outside the run that assigned them. A ``cell_id`` is only
unique within its cell model, so it is the pair that names a cell.

``device`` is stamped by the :class:`~bsb.simulation.results.SimulationResult`
rather than by each recorder, so a new backend cannot forget to record where a
signal came from. A recorder that annotates a device itself keeps its own answer.

Devices add their own annotations on top. A multimeter recording several
properties, for instance, marks each signal with the property it sampled.

Reading results
===============

A recording names its cell, but only the network can say where that cell is or
what it is. :func:`~bsb.simulation.results.read_results` reads a results file
together with the network it was simulated on:

.. code-block:: python

    from bsb import read_results

    results = read_results("network.hdf5", "simulation-results/run.nio")
    for recording in results.recordings("my_spike_recorder"):
        print(recording.cell.id, recording.cell.position, len(recording.signal))

Each recording carries a :class:`~bsb.simulation.results.RecordedCell` as
``recording.cell``: its ``id``, the name of its cell ``model``, the network's
``cell_type`` and ``placement_set``, and its ``position``. A device level record
has no cell, and its ``cell`` is ``None``. A device's recordings are all of the cells
it targeted, including the ones that stayed silent.

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
  since.
* A run that recorded no network identity also warns, since the pair cannot be
  verified.

The results file does not say where its network is. Paths move, and a stored path
would leak local directories into shared files, so the caller passes both.

Reading a bare results file
---------------------------

Without the network, :func:`~bsb.simulation.results.iter_recordings` walks the
recordings of a block, a segment, or a list of either, and yields a
:class:`~bsb.simulation.results.Recording` for each: the device, the cell model, the
cell id, and the Neo object itself. It takes the containers Neo keeps separate
(spike trains, analog signals) and presents them as one sequence, so reading does
not depend on which kind of device made the data.

.. code-block:: python

    from bsb.simulation.results import iter_recordings

    # every recording of one device
    for recording in iter_recordings(block, device="spikes_exc"):
        print(recording.cell_model, recording.cell_id, len(recording.signal))

    # everything recorded from one cell, across devices
    for recording in iter_recordings(block, cell_model="granule_cell", cell_id=42):
        print(recording.device, recording.signal)

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
