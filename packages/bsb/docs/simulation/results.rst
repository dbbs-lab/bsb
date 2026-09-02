==================
Simulation results
==================

A simulation writes its results to a `Neo <https://neo.readthedocs.io>`_ file: one
``.nio`` per run, whatever number of MPI ranks produced it.

What is in a results file
=========================

Recorded objects are ordinary Neo :class:`~neo.core.SpikeTrain` and
:class:`~neo.core.AnalogSignal` objects, so anything that reads Neo reads them. What
BSB adds is annotations saying *where each one came from*, as flat values you can
read without decoding anything:

======================== ==========================================================
``bsb_device_name``      The device that produced it, as you named it.
``bsb_device_kind``      What kind of device that is, e.g. ``spike_recorder``.
``bsb_recording_kind``   What is addressed: ``cell``, or ``point`` for a location
                         on a morphology.
``bsb_direction``        ``record`` when data came out of the network,
                         ``stimulate`` when a device put it in.
``bsb_ps_name``          Placement set the cell belongs to.
``bsb_cell_id``          Index of the cell within that placement set.
``bsb_cell_model``       Cell model it was simulated as.
``bsb_branch``,          Where on the morphology, for ``point`` recordings.
``bsb_point``,
``bsb_arc``
``bsb_mpi_rank``         Which rank simulated that cell.
``bsb_simulation_id``    Which run.
``bsb_segment_id``       Which flush within the run.
======================== ==========================================================

Recording kind and direction are separate questions on purpose. A stimulator's own
output addresses the same things a recorder does, with the data flowing the other
way, so it is a ``direction`` rather than a kind of its own.

.. note::

    The ``synapse`` and ``lfp`` recording kinds are not shipped yet. They arrive with
    the LFP probe, so that no kind exists without something producing it.

Silent cells
============

A recorder emits an object for each cell **it actually observed**. A cell that never
spiked leaves nothing behind, rather than an empty recording.

What each device was pointed at is stored instead, under ``devices`` in the run's
provenance. The three questions then have exact answers, without writing an empty
object per silent cell:

* *which cells did this device record?* — the stored target set;
* *which of them fired?* — the objects in the file;
* *which stayed silent?* — the difference.

For a population of 100 000 cells at 1% activity, that is a thousand recordings and
one list of ids, rather than a hundred thousand mostly-empty recordings.

.. code-block:: python

    from bsb import read_nio, silent_cells

    block = read_nio("results.nio")[0]
    print(silent_cells(block, "my_recorder"))   # {'granule': [1, 3, ...]}

Finding things in a file
========================

:func:`iter_recordings <bsb:bsb.simulation.results.iter_recordings>` walks everything
recorded in a block, filtered on any annotation above:

.. code-block:: python

    from bsb import iter_recordings, read_nio

    block = read_nio("results.nio")[0]

    for recording in iter_recordings(block, ps_name="granule"):
        print(recording.device, recording.cell_id, recording.data)

    # Only what a device put into the network, rather than what it observed.
    stimuli = list(iter_recordings(block, direction="stimulate"))

    # Only recordings from a location on a morphology.
    points = list(iter_recordings(block, recording_kind="point"))

Objects that do not follow the convention -- output from a plugin doing its own thing
-- are yielded too, with empty fields, so you can see they are there rather than have
them silently skipped.

:func:`read_nio <bsb:bsb.simulation.results.read_nio>` returns **every** block in the
file. Results are appended, so one file holds one block per run.

Running with MPI
================

Each rank writes its own part into ``<results>.nio.ranks/``, and rank 0 merges them
into the file you asked for once every rank has finished. The parts are removed on
success, so **a run ends with one file at the path you named**, whatever the rank
count.

Ranks record disjoint cells, so merging is a concatenation: nothing is reconciled or
dropped. Segments line up on their ``checkpoint_index``.

If the merge fails, the parts are **kept** and their location reported. They are the
only copy of a completed run's results, and losing them to a tidy-up would be worse
than leaving them behind.

.. note::

    A shared file is not used because ``nixio`` cannot open one for parallel writing:
    it never configures an MPI file driver, and its create-or-open would be a race
    between ranks besides.

Provenance
==========

Every results file records the run that made it: the BSB and plugin versions, the
simulation's name, duration and resolution, the seed it drew, and a back-reference to
the reconstruction it ran against by ``storage_id`` and ``state_id``. That is what
lets a recording be traced to the exact network state that produced it.

.. code-block:: python

    from neo import io

    from bsb import read_provenance, read_simulation_config

    block = io.NixIO("results.nio", "ro").read_all_blocks()[0]

    provenance = read_provenance(block)
    print(provenance["simulation_id"], provenance["scaffold"]["storage_id"])

    # The configuration that actually ran, including any seed it drew.
    config = read_simulation_config(block)

Feeding that configuration back reproduces the run: see :doc:`/core/randomness`.

Reading a file from a different BSB
===================================

Both readers **degrade rather than refuse**. A provenance bundle written by a newer
BSB warns and returns what is recognised; a configuration written before configurations
were stored intact warns and returns what is there. The recordings themselves are plain
Neo and readable regardless, and refusing a file over its metadata would keep you from
results that are perfectly intact.
