Usage
=====


.. image:: https://dbbs-static.s3.eu-south-1.amazonaws.com/misc/how-to-patch.gif
   :alt: Inline replacement of NEURON by Patch


Be aware that the interface is currently incomplete, this means that most parts are still
"just" NEURON. I've only patched holes I frequently encounter myself when using NEURON's
:class:`~neuron.h.Section`, :class:`NetStim <neuron:NetStim>` and :class:`NetCon
<neuron:Netcon>` functions. Feel free to open an issue or fork this project and open a
pull request for missing or broken parts of the interface.

Philosophy
----------

Python interfaces should be Pythonic, this wrapper offers just that:

* Full Python objects: each wonky C-like NEURON object is wrapped in a full
  fledged Python object, easily handled and extended through inheritance.
* Duck typed interface: take a look at the magic methods I use and any object
  you create with those methods present will work just fine with Patch.
* Correct garbage collection, objects connected to eachother don't dissapear:
  Objects that rely on eachother store a reference to eachother. As is the basis
  for any sane object oriented interface.

Basic usage
-----------

Use it like you would use NEURON. The wrapper doesn't make many changes to the
interface, it just patches up some of the more frequent and ridiculous gotchas.

Patch supplies a new HOC interpreter ``p``, the
:class:`~.interpreter.PythonHocInterpreter` which wraps the standard HOC interpreter
:class:`neuron.h` provided by NEURON. Any objects returned will either be
:class:`~.objects.PythonHocObject`'s wrapping their corresponding NEURON object, or
whatever NEURON returns.

When using just Patch the difference between NEURON and Patch objects is handled
transparently, but if you wish to mix interpreters you can transform all Patch objects
back to NEURON objects with :meth:`~.objects.PythonHocObject.__neuron__` or the helper
function :func:`.transform`.

.. code-block:: python

   from patch import p, transform
   import glia as g

   section = p.Section()
   point_process = g.insert(section, "AMPA")
   stim = p.NetStim()
   stim.start = 10
   stim.number = 5
   stim.interval = 10

   # And here comes the magic! This explicitly defined connection
   # isn't immediatly garbage collected! What a crazy world we live in.
   # Has science gone too far?
   p.NetCon(stim, point_process)

   # It's fully compatible using __neuron__
   from neuron import h
   nrn_section = h.Section()
   nrn_section.connect(transform(section))
   nrn_section.connect(section.__neuron__())
