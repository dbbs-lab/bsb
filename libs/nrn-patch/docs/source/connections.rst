#####################
Connecting components
#####################

===================
Connecting sections
===================

To other sections
=================

Connecting sections together is the basic way of constructing cells in NEURON. You can
do so using the :meth:`.Section.connect` method.

.. code-tabs::

  .. code-tab:: python
    :title: Patch

    from patch import p
    s = p.Section()
    s2 = p.Section()
    s.connect(s2)

  .. code-tab:: python
    :title: NEURON

    from neuron import h
    s = h.Section()
    s2 = h.Section()
    s.connect(s2)


===================
Network connections
===================

TO DO



In parallel simulations
=======================


In Patch most of the parallel context is managed for you, and you can use the
:func:`~.interpreter.PythonHocInterpreter.ParallelCon` method to either connect
an output (cell soma, axons, ...) to a GID or a GID to an input (synapse on
postsynaptic cell, ...).

The following code transmits the spikes of a Section on GID 1:

.. code-tabs::

  .. code-tab:: python
    :title: Patch

    from patch import p
    gid = 1
    s = p.Section()
    nc = p.ParallelCon(s, gid)

  .. code-tab:: python
    :title: NEURON

    from neuron import h
    gid = 1
    h.nrnmpi_init()
    pc = h.ParallelContext()
    s = h.Section()
    nc = h.NetCon(s(0.5)._ref_v, None)
    pc.set_gid2node(gid, pc.id())
    pc.cell(gid, nc)
    pc.outputcell(gid)


You can then receive the spikes of GID 1 on a synapse:

.. code-tabs::

  .. code-tab:: python
    :title: Patch

    from patch import p
    gid = 1
    syn = p.Section().synapse(p.SynExp)
    nc = p.ParallelCon(gid, syn)

  .. code-tab:: python
    :title: NEURON

    from neuron import h
    gid = 1
    h.nrnmpi_init()
    pc = h.ParallelContext()
    s = h.Section()
    syn = h.SynExp(s)
    pc.gid_connect(gid, syn)
