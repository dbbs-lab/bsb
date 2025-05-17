###########
Candy Guide
###########

Read through this guide to get an idea of the sugar you're getting.

===========
Referencing
===========

All objects in Patch that depend on each other reference each other, meaning that Python
won't garbage collect parts of your simulation that you explicitly defined. An example of
this is that when you create a synapse and a NetStim and connect them together with a
NetCon, you only have to hold on to 1 of the variables for Patch to know that if you're
holding on to a NetCon you are *most likely* interested in the parts it is connected to.
There is no longer a need to store every single NEURON variable in a list or on an object
somewhere. This drastically cleans up your code.

===================
Sections & Segments
===================

* When connecting Sections together they all reference each other.
* Whenever you're using a Section where a Segment is expected, a default Segment will be
  used (Segment 0.5):

.. code-block:: python

  s = p.Section()
  syn = p.ExpSyn(s)
  # syn = h.ExpSyn(s(0.5))

* Whenever a Section/Segment is recorded or connected and a NEURON scalar is expected
  ``_ref_v`` is used:

.. code-block:: python

  s = p.Section()
  v = p.Vector()
  v.record(s) # v.record(s(0.7)._ref_v)

* Sections can record themselves at multiple points:

.. code-block:: python

  s = p.Section()
  s.record() # Creates a vector, makes it record s(0.5)._ref_v and stores it as a recorder
  s.record(0.7) # Records s(0.5)._ref_v

  plt.plot(list(s.recordings[0.5]), list(p.time))

* Sections can connect themselves to a PointProcess target with ``.connect_points``, which
  handles NetCon stack access transparently. This allows for example for easy creation of
  synaptic contacts between a Section and a target synapse:

.. code-block:: python

  s = p.Section()
  target_syn = p.Section().synapse(p.ExpSyn) # Creates an ExpSyn synapse
  s.connect_synapse(target_syn) # Creates a NetCon between s(0.5)._ref_v and target_syn

* Create a current clamp in a Section and configure it with keyword arguments:

.. code-block:: python

  clamp = p.Section().iclamp(amp=10, delay=0, duration=100)
  # Pass an array to inject a varying current per timestep starting from the delay.
  clamp2 = p.Section().iclamp(amp=[i for i in range(1000)], delay=100)

* You can place Sections on the stack with ``.push()``, ``.pop()`` or a context manager:

.. code-block:: python

  s = p.Section()
  s.push()
  s.pop()
  with s.push():
    s_clamp = p.IClamp()
  # `s` is automatically popped from the stack when the context is exited.

* `p.SectionRef` can be called with either an arg or ``sec`` kwarg:

.. code-block:: python

  s = p.Section()
  sr = p.SectionRef(sec=s)
  sr = p.SectionRef(s)

=================
Parallel networks
=================

When you get to the level of the network the work becomes alot easier if you can describe
your cells in a more structured way, so be sure to check out `Arborize
<https://arborize.readthedocs.io/en/latest/>`_.

If you want to stay vanilla Patch still has you covered; it comes with out-of-the-box
parallelization. Introducing the transmitter-receiver pattern:

.. code-block:: python

  if p.parallel.id() == 0:
    transmitter = ParallelCon(obj1, gid)
  if p.parallel.id() == 1:
    receiver = ParallelCon(gid, obj2)

Just these 2 commands will create a transmitter on node 0 that broadcasts the spikes of
``obj1`` (sections, segments) with the specified GID and a receiver on node 1 for ``obj2``
(synapses, most likely?) that listens to spikes with that GID. Know that under the hood it
needs to be something that can be connected to a ``NetCon``.

That's it. You are now spiking in parallel!

Arbitrary data broadcasting
===========================

MPI has a great feature, it allows broadcasting data to other nodes. In NEURON this is
restricted to just Vectors. Patch gives you back the freedom to transmit arbitrary data.
Anything that can be pickled can be transmitted:

.. code-block:: python

  data = None # It's important to declare your var on all nodes to avoid NameErrors
  if p.parallel.id() == 12:
    data = np.random.randint((12,12,12))
  received = p.parallel.broadcast(data, root=12)
