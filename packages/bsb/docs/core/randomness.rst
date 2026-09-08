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
      "generators": {
        "structure": { "seed": 42 }
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

The block is the generator
==========================

The :guilabel:`rng` block is itself the generator everything draws from unless it says
otherwise, so a configuration that says nothing but a seed already has one and no entry
appears that you did not write.

Its :guilabel:`bit_generator` names the :mod:`numpy` bit generator behind the draws. It
is named rather than left to :func:`numpy.random.default_rng`, whose choice may change
between releases and would take every stream in every model with it.

Holding one part fixed
======================

A :guilabel:`generators` entry is a named source to draw from. One with its own
:guilabel:`seed` is pinned and does not move between runs; one without derives from the
root seed like everything else.

A component names the one it draws from, so what it uses stands in the configuration:

.. code-block:: json

    "rng": {
      "generators": { "structure": { "seed": 42 } }
    },
    "placement": {
      "granule_layer": { "strategy": "...", "rng": "structure" }
    }

That is what separates the two kinds of replicate. Point placement at a pinned generator
and every run builds the same network with different simulation noise. Name nothing and
the network varies too.

A name that does not exist is an error when the configuration is booted, rather than a
different stream drawn in silence.

Seeding something that seeds itself
===================================

A simulator kernel is not drawn from: it wants a number of its own and makes its own
randomness out of it. Those go in :guilabel:`settings`, which a backend registers a kind
into, and a simulation names the one it uses:

.. code-block:: json

    "rng": {
      "settings": { "kernel": { "strategy": "nest", "seed": 999 } }
    }

How many numbers a subsystem wants is its own business. One kernel seed is one
:meth:`derive <bsb:bsb.rng.RngSettings.derive>` with no key; a backend that seeds per
object calls it once per key and gets as many distinct numbers as it has objects.

Streams are derived from the data, not the rank
===============================================

:meth:`rng <bsb:bsb.rng.NumpyRng.rng>` takes a **key**: what the draws are
*for*, such as a chunk, a cell type, a device or a connection tag.

.. code-block:: python

    rng = self.get_rng(key=(chunk, cell_type.name))
    positions = rng.random((n, 3))

The key is not a count of anything -- it is the identity of the stream. A generator with
a one-element key hands out as many numbers as one with six.

The key never includes the MPI rank. That is deliberate, and it is what makes a run
reproduce across a different number of ranks: if a stream were seeded per rank, or drawn
sequentially from one generator, each rank would consume a different amount of it and
changing the rank count would change every result.

Two calls with the same key give the same stream, so a component does not have to hold
on to a generator to stay reproducible -- it can ask for the one belonging to whatever
it is about to draw for.

.. note::

    Keys are hashed stably rather than with Python's built-in ``hash``, which is salted
    per process and would reseed differently on every invocation. The encoding tags each
    element with its kind and leads with its own length, so ``None`` is not the integer
    ``0``, and a key ending in a zero is not the key without it.

.. warning::

    Not every component draws through this service yet. Those that do not still use an
    unseeded global generator, and are neither reproducible nor recorded. They are being
    converted; until a component is, its randomness is outside the guarantees above.
