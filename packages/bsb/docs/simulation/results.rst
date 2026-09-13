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
type, and any per-cell annotation a device or a downstream tool wants to add.
Neuroscience is numerous by design, and the tools downstream of Neo are built to
handle many objects.

Cells that produced nothing write nothing. A cell that never fired has no spike
train, and its silence is legible as its absence: there is no empty placeholder to
distinguish from a real, empty recording. The device's target count travels with
the recordings, so a population rate is the recorded trains summed over that
count, not over the number of trains.

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
   * - ``cell_id``
     - The cell the recording belongs to. Absent for a device level record, such
       as a generator's own spikes.
   * - ``cell_type``
     - Name of the cell model, where the backend knows it.

``device`` is stamped by the :class:`~bsb.simulation.results.SimulationResult`
rather than by each recorder, so a new backend cannot forget to record where a
signal came from. A recorder that annotates a device itself keeps its own answer.

Devices add their own annotations on top. A multimeter recording several
properties, for instance, marks each signal with the property it sampled.

Reading results
===============

:func:`~bsb.simulation.results.iter_recordings` walks the recordings of a block, a
segment, or a list of either, and yields a
:class:`~bsb.simulation.results.Recording` for each: the device, the cell, the
cell type, and the Neo object itself. It takes the containers Neo keeps separate
(spike trains, analog signals) and presents them as one sequence, so reading does
not depend on which kind of device made the data.

.. code-block:: python

    from bsb.simulation.results import iter_recordings

    # every recording of one device
    for recording in iter_recordings(block, device="spikes_exc"):
        print(recording.cell_id, recording.cell_type, len(recording.signal))

    # everything recorded from one cell, across devices
    for recording in iter_recordings(block, cell_id=42):
        print(recording.device, recording.signal)

To count a population's spikes, sum the trains of its device:

.. code-block:: python

    recordings = list(iter_recordings(block, device="spikes_exc"))
    n_spikes = sum(len(recording.signal) for recording in recordings)
    pop_size = recordings[0].signal.annotations["pop_size"]
    rate = n_spikes / duration * 1000.0 / pop_size

Provenance
==========

Alongside the results, the block records what produced them:
:func:`~bsb.simulation.results.read_simulation_config` returns the configuration
of the simulation that ran, and
:func:`~bsb.simulation.results.read_provenance` returns the run's provenance. Both
read a block, whether it came from a
:class:`~bsb.simulation.results.SimulationResult` or from a file.
