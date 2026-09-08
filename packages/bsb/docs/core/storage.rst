#######
Storage
#######

The :class:`Storage <bsb:bsb.storage.Storage>` object owns the on-disk artefact
that holds a reconstructed network. It is reachable from any
:class:`Scaffold <bsb:bsb.core.Scaffold>` via
:attr:`scaffold.storage <bsb:bsb.core.Scaffold.storage>`, and is parameterised by
two things:

* an **engine** (chosen via the :guilabel:`storage.engine` configuration key) that
  picks the on-disk format;
* a **root** (chosen via :guilabel:`storage.root`), the path the engine writes to.

The engine is loaded from the ``bsb.storage.engines`` plugin category (see
:ref:`plugins`); two engines ship by default,
:class:`fs <bsb:bsb.storage.fs.FileSystemEngine>` and
:class:`hdf5 <bsb_hdf5:bsb_hdf5.HDF5Engine>`.

Storage engines
===============

FS
--

A lightweight filesystem-backed engine
(:class:`FileSystemEngine <bsb:bsb.storage.fs.FileSystemEngine>`). The root is a
**directory** containing a ``metadata.json`` plus two subfolders:

* ``files/``: opaque files stored by the
  :class:`FileStore <bsb:bsb.storage.interfaces.FileStore>` (typically the active
  configuration JSON and any user-attached blobs).
* ``file_meta/``: sidecar metadata for each file (mtime, encoding, content hash,
  producer).

The FS engine does **not** store placement or connectivity data; those raise
:class:`NotImplementedError` on this backend. It exists for workflows that only
need the configuration and file-store side of a storage object, for example
distributing a config bundle without a compiled network.

HDF5
----

The full storage backend (:class:`HDF5Engine <bsb_hdf5:bsb_hdf5.HDF5Engine>`), used
for compiled networks. The root is a **single HDF5 file**. Top-level layout:

* ``/placement/<cell_type>``: one group per
  :class:`PlacementSet <bsb:bsb.storage.interfaces.PlacementSet>`, containing the
  per-chunk position, rotation, morphology and label datasets.
* ``/connectivity/<tag>``: one group per
  :class:`ConnectivitySet <bsb:bsb.storage.interfaces.ConnectivitySet>`, holding
  incoming and outgoing per-chunk connection blocks.
* ``/files/<uuid>``: file store (active configuration JSON and any user blobs),
  with per-file meta stored as a JSON-encoded ``meta`` attribute on each dataset.
* ``/morphologies``: the
  :class:`MorphologyRepository <bsb:bsb.storage.interfaces.MorphologyRepository>`,
  content-addressed by hash in the morphology metadata.

Concurrent reader safety, locking, and slow-lock diagnostics are handled by the
engine; component code does not need to manage these.

The on-disk artefact also carries a provenance bundle (storage identity, plugin
manifest, host info, timestamps, per-PlacementSet revision counters, ...). Plugin
authors and operators that need the full bundle layout should consult
:ref:`storage-engine-contract`.
