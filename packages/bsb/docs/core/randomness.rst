===========
Randomness
===========

A model that draws randomly has two demands on it that pull in opposite directions.
Running it repeatedly has to give **technical replicates**, runs that differ only in
their randomness, or an average over them is an average over one sample. And any one
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
result is not the one you wrote; it is the one that ran.

**Feed a recorded configuration back and it reproduces.** The difference between the
configuration you wrote and the one a run recorded is nothing but seed values, so
pasting the recorded seed back reproduces that run exactly:

.. code-block:: json

    "rng": { "seed": 2866720059 }

.. warning::

    **Never aggregate over runs that share a seed.** Repeating a run with the same seed
    does not give a sample of size *n*. It gives one run, copied *n* times. Every
    repetition draws the same numbers, so it carries the same artifacts of the same
    draws, and a mean over the set is the mean of a single observation while its spread
    collapses towards zero for reasons that have nothing to do with the model.

    Five runs drawing three numbers each, from a distribution whose true mean is 20:

    .. code-block:: text

        fixed seed                    seed left unset

        37 25 27   mean 29.7           5  5 31   mean 13.7
        37 25 27   mean 29.7          24 10 38   mean 24.0
        37 25 27   mean 29.7          35 34 32   mean 33.7
        37 25 27   mean 29.7           6 33 26   mean 21.7
        37 25 27   mean 29.7          37 27 28   mean 30.7

        29.67 ± 0.00  (n=5)           24.73 ± 7.03  (n=5)

    The left column looks like the better measurement and is the worse one. It reports
    zero uncertainty about a value that is ten away from the truth, because its five
    runs are one run counted five times. Adding a sixth changes neither number.

    The right column is honest about how little five runs tell you, and it is the only
    one of the two that moves towards 20 as runs are added. A mean over independent
    replicates approximates the parameter; a mean over repetitions of one seed
    approximates nothing.

    A test run on the left-hand set reports power the data does not have. Random samples
    have to be **independent** of one another, and repetitions of a fixed seed are not
    independent; they are identical.

    Leave :guilabel:`seed` unset when you need a set of runs to average over, and every
    run is an independent replicate. Set a seed only to reproduce one particular run, or
    to hold one named part of a model fixed while the rest of it varies.

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

The key is not a count of anything; it is the identity of the stream. A generator with
a one-element key hands out as many numbers as one with six.

The key never includes the MPI rank. That is deliberate, and it is what makes a run
reproduce across a different number of ranks: if a stream were seeded per rank, or drawn
sequentially from one generator, each rank would consume a different amount of it and
changing the rank count would change every result.

Two calls with the same key give the same stream, so a component does not have to hold
on to a generator to stay reproducible; it can ask for the one belonging to whatever
it is about to draw for.

.. note::

    Keys are hashed stably rather than with Python's built-in ``hash``, which is salted
    per process and would reseed differently on every invocation. The encoding tags each
    element with its kind and leads with its own length, so ``None`` is not the integer
    ``0``, and a key ending in a zero is not the key without it.

Writing a generator of your own
===============================

:guilabel:`generators` takes any kind registered into its class map, so a plugin can
ship one the way it ships a placement strategy. What the block asks of a kind is one
method: hand back something a component can draw from.

.. code-block:: python

    from bsb import Rng, config

    @config.node
    class MyRng(Rng, classmap_entry="mine"):
        def rng(self, key=()):
            ...  # returns a numpy.random.Generator

Register it through the ``bsb.components`` entry point like any other component, and a
model names it with ``"strategy": "mine"``.

Almost every kind you would write differs in *how it seeds*, not in the arithmetic
underneath. Those need nothing from :mod:`numpy` beyond what is already there: pick one
of its bit generators and seed it your way, which is all
:class:`NumpyRng <bsb:bsb.rng.NumpyRng>` itself does.

.. note::

    A genuinely new algorithm is a bigger undertaking than it looks. :mod:`numpy` only
    accepts a bit generator that implements its C-level ``bitgen_t`` struct, so it has
    to be written in Cython, C or Numba rather than Python. `Extending NumPy's random
    number generation
    <https://numpy.org/doc/stable/reference/random/extending.html>`_ walks through it.

    Returning a :class:`numpy.random.Generator` is deliberate rather than incidental:
    every component that draws calls ``random``, ``integers`` or ``choice`` on what it
    is handed, so a kind that answered with something else would break all of them.

.. warning::

    Not every component draws through this service yet. Those that do not still use an
    unseeded global generator, and are neither reproducible nor recorded. They are being
    converted; until a component is, its randomness is outside the guarantees above.
