===========
Randomness
===========

A model that draws randomly has two demands on it that pull in opposite directions.
Running it repeatedly has to give **technical replicates** -- runs that differ only in
their randomness -- or an average over them is an average over one sample. And any one
of those runs has to be **reproducible** afterwards, or a result cannot be checked.

The :guilabel:`rng` block gives both, by making an unset seed mean *draw one and write
it down*.

.. code-block:: json

    "rng": {
      "seed": null,
      "providers": {
        "placement": { "seed": 42 }
      }
    }

Replicates and reproduction
===========================

**Leave the seed unset and every run is a replicate.** A fresh root seed is drawn when
the configuration is booted, and every stream in the model derives from it, so no two
runs draw the same numbers.

**Each run records the seed it used.** The resolved seed is written into the
configuration stored with that run's output, so the configuration you get back out of a
result is not the one you wrote -- it is the one that ran.

**Feed a recorded configuration back and it reproduces.** The difference between the
configuration you wrote and the one a run recorded is nothing but seed values, so
pasting the recorded seed back reproduces that run exactly:

.. code-block:: json

    "rng": { "seed": 2866720059 }

Holding one part fixed
======================

A :guilabel:`providers` entry is a named source of randomness. One with its own
:guilabel:`seed` is pinned and does not move between runs; one without derives from the
root seed like everything else.

That is what separates the two kinds of replicate. Pin :guilabel:`placement` and every
run builds the same network with different simulation noise. Pin nothing and the network
varies too.

Streams are derived from the data, not the rank
===============================================

:meth:`get_rng <bsb:bsb.rng.RandomNode.get_rng>` takes a **key**: what the draws are
*for*, such as a chunk, a cell type, a device or a connection tag.

.. code-block:: python

    rng = network.configuration.rng.get_rng("placement", key=(chunk, cell_type.name))
    positions = rng.random((n, 3))

The key never includes the MPI rank. That is deliberate, and it is what makes a run
reproduce across a different number of ranks: if a stream were seeded per rank, or drawn
sequentially from one generator, each rank would consume a different amount of it and
changing the rank count would change every result.

Two calls with the same key give the same stream, so a component does not have to hold
on to a generator to stay reproducible -- it can ask for the one belonging to whatever
it is about to draw for.

.. note::

    Keys are hashed stably rather than with Python's built-in ``hash``, which is salted
    per process and would reseed differently on every invocation.

.. warning::

    Not every component draws through this service yet. Those that do not still use an
    unseeded global generator, and are neither reproducible nor recorded. They are being
    converted; until a component is, its randomness is outside the guarantees above.
