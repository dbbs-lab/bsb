#######################
Morphology repositories
#######################

Morphology repositories (MRs) are an interface of the :mod:`bsb:bsb.storage` module and can be
supported by the :class:`bsb:bsb.storage.interfaces.Engine` so that morphologies can be stored
inside the network storage.

To access an MR, a :class:`bsb:bsb.storage.Storage` object is required:

.. code-block:: python

  from bsb import Storage

  store = Storage("hdf5", "morphologies.hdf5")
  mr = store.morphologies
  print(mr.all())

Similarly, the built-in MR of a network is accessible as ``network.morphologies``:

.. code-block:: python

  from bsb import from_storage

  network = from_hdf("my_existing_model.hdf5")
  mr = network.morphologies

You can use the :meth:`bsb:bsb.storage.interfaces.MorphologyRepository.save` method to store
:class:`Morphologies <bsb:bsb.morphologies.Morphology>`. If you don't immediately need the whole
morphology, you can :meth:`bsb:bsb.storage.interfaces.MorphologyRepository.preload` it,
otherwise you can load the entire thing with
:meth:`bsb:bsb.storage.interfaces.MorphologyRepository.load`.

.. autoclass:: bsb.storage.interfaces.MorphologyRepository
  :noindex:
  :members:
