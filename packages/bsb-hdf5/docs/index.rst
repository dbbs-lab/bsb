BSB HDF5 storage engine
=======================

``bsb-hdf5`` is the default storage engine for the BSB. It persists a network
(placement, connectivity, morphologies, files) to a single HDF5 file and
mediates concurrent rank access via an ``MPILock``.

This site contains the narrative dev docs and the auto-generated API reference.
For end-user configuration of the storage block, see the main
`BSB documentation <https://bsb.readthedocs.io/en/latest/index.html>`_.

.. toctree::
   :maxdepth: 2
   :caption: Architecture

   architecture
   handles
   chunking
   resources
   telemetry

.. toctree::
   :maxdepth: 2
   :caption: Reference

   bsb_hdf5/modules
   genindex
   py-modindex
