Sections
========

Sections are cilindrical representations of pieces of a cell. They have a length and a
diameter. Sections are the main building block of a simulation in NEURON.

You can use the :meth:`~.objects.Section.connect` method to connect :class:`Sections
<.objects.Section>` together.

Sections can be subdivided into :class:`Segments <.objects.Segment>` by specifying
``nseg``, the simulator calculates the voltage for each segment, thereby affecting the
spatial resolution of the simulation. The position of a segment is represented by its
normalized position along the axis of the Segment. This means that a Segment at x=0.5
is in the middle of the Section. By default every section consists of 1 segment and
the potential will be calculated for 3 points: At the start (0) and end (1) of the
section, and in the middle of every segment (0.5). For 2 segments the simulator would
calculate at 0, 0.333..., 0.666... and 1.

.. code-tabs::

  .. code-tab:: python
    :title: Patch

    from patch import p
    s = p.Section()
    s.L = 40
    s.diam = 0.4
    s.nseg = 11

    s2 = p.Section()
    s.connect(s2)

  .. code-tab:: python
    :title: NEURON

    from neuron import h
    s = h.Section()
    s.L = 40
    s.diam = 0.4
    s.nseg = 11

    s2 = h.Section()
    s.connect(s2)

Retrieving segments
-------------------


:class:`Sections <.objects.Section>` can be called with an x to retrieve the segment at
that x. The segments of a :class:`~.objects.Section` can also be iterated over.

.. code-tabs::

  .. code-tab:: python
    :title: Patch

    s.nseg = 5
    seg05 = s(0.5)
    print(seg05)
    for seg in s:
        print(seg)

  .. code-tab:: python
    :title: NEURON

    s.nseg = 5
    seg05 = s(0.5)
    print(seg05)
    for seg in s:
        print(seg)

Recording
---------

You can tell Patch to record the membrane potential of your :class:`~.objects.Section` at
one or multiple locations by calling the ``.record`` function and giving it an ``x``. If
``x`` is omitted ``0.5`` is used.

In NEURON you'd have to create a :class:`Vector <.objects.Vector>` and keep track of it
somewhere and find a way to link it back to the :class:`~.objects.Section` it recorded, in
Patch a section automatically stores its recording vectors in ``section.recordings``.

.. code-tabs::

  .. code-tab:: python
    :title: Patch

        s.record(x=1.0)

  .. code-tab:: python
    :title: NEURON

          v = h.Vector()
          v.record(s(1.0))
          all_recorders.append(v)

Position in space
-----------------

With Patch it's very straightforward to define the 3D path of your Section through
space. Call the ``.add_3d`` function with a 2D array containing the xyz data of your
points. Optionally, you can pass another array of diameters.


.. code-tabs::

  .. code-tab:: python
    :title: Patch

    s.add_3d([[0, 0, 0], [2, 2, 2]], diameters)

  .. code-tab:: python
    :title: NEURON

    s.push()
    points = [[0, 0, 0], [2, 2, 2]]
    for point, diameter in zip(points, diameters):
      h.pt3dadd(*point, diameter)
    h.pop_section()

Full reference
--------------

Here is a full list of methods that Patch patched or added to the interface of
:class:`NEURON Sections <neuron.h.Section>`:

.. autoclass:: patch.objects.Section
  :members:
  :noindex:
