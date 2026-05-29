.. _storage-engine-contract:

Storage engines
===============

**Plugin category:** ``bsb.storage.engines``

A storage engine is an :class:`Engine <bsb:bsb.storage.interfaces.Engine>` subclass
that persists a reconstruction (placement, connectivity, files, morphologies). The
two reference implementations are :mod:`bsb_hdf5 <bsb_hdf5:bsb_hdf5>` (full
reconstruction, HDF5-backed, see :class:`HDF5Engine
<bsb_hdf5:bsb_hdf5.HDF5Engine>`) and :mod:`bsb-core <bsb:bsb>`'s
:class:`FileSystemEngine <bsb:bsb.storage.fs.FileSystemEngine>` (filesystem layout,
metadata-only).

Engine ABC
----------

The :class:`Engine <bsb:bsb.storage.interfaces.Engine>` ABC has two groups of
abstract members. The lifecycle group covers
:meth:`create <bsb:bsb.storage.interfaces.Engine.create>`,
:meth:`move <bsb:bsb.storage.interfaces.Engine.move>`,
:meth:`copy <bsb:bsb.storage.interfaces.Engine.copy>`,
:meth:`remove <bsb:bsb.storage.interfaces.Engine.remove>`,
:meth:`exists <bsb:bsb.storage.interfaces.Engine.exists>`,
:meth:`clear_placement <bsb:bsb.storage.interfaces.Engine.clear_placement>`, and
:meth:`clear_connectivity <bsb:bsb.storage.interfaces.Engine.clear_connectivity>`.
The provenance surface (below) is the second group.

:attr:`metadata <bsb:bsb.storage.interfaces.Engine.metadata>` (property)
    Returns the root-level provenance bundle as a JSON-serialisable :class:`dict`.
    The canonical layout is built by
    :func:`build_root_metadata <bsb:bsb.storage.provenance.build_root_metadata>`; persist its output verbatim
    on :meth:`create <bsb:bsb.storage.interfaces.Engine.create>`. Return ``{}`` if
    the engine is opened read-only against an artefact that lacks a bundle and
    cannot be upgraded.

:meth:`_bump_state <bsb:bsb.storage.interfaces.Engine._bump_state>`
    Increments :attr:`state_id <bsb:bsb.storage.interfaces.Engine.state_id>`
    atomically. The engine invokes this itself from every mutating code path:
    :meth:`clear_placement <bsb:bsb.storage.interfaces.Engine.clear_placement>`,
    :meth:`clear_connectivity <bsb:bsb.storage.interfaces.Engine.clear_connectivity>`,
    :meth:`FileStore.store <bsb:bsb.storage.interfaces.FileStore.store>` and
    :meth:`FileStore.remove <bsb:bsb.storage.interfaces.FileStore.remove>`,
    :class:`PlacementSet <bsb:bsb.storage.interfaces.PlacementSet>` and
    :class:`ConnectivitySet <bsb:bsb.storage.interfaces.ConnectivitySet>` mutators.
    No-op when the engine is in read-only mode.

``_upgrade_if_needed``
    Called from ``__init__`` after ``super().__init__``. Detects an existing
    artefact missing the provenance bundle, stamps a fresh ``storage_id`` and the
    rest of the bundle with current values, and emits a single
    :class:`BsbProvenanceUpgradeWarning
    <bsb:bsb.exceptions.BsbProvenanceUpgradeWarning>`. No-op for fresh artefacts
    (already stamped by :meth:`create <bsb:bsb.storage.interfaces.Engine.create>`),
    read-only engines, and roots that do not exist yet.

Every mutator that writes to disk must call
:meth:`_bump_state <bsb:bsb.storage.interfaces.Engine._bump_state>` (or the local
equivalent that updates the root attrs in the same open handle) so the counter
stays in sync with reality.

The provenance bundle
---------------------

Every storage root carries this bundle. It is exposed read-only on the
:class:`Scaffold <bsb:bsb.core.Scaffold>` as
:attr:`scaffold.storage_id <bsb:bsb.core.Scaffold.storage_id>` (UUID4, immutable),
:attr:`scaffold.state_id <bsb:bsb.core.Scaffold.state_id>` (monotonic int) and
:attr:`scaffold.provenance <bsb:bsb.core.Scaffold.provenance>` (the full dict).

============================== ==============================================================
Key                            Meaning
============================== ==============================================================
``storage_id``                 UUID4, immutable.
``state_id``                   Monotonic revision counter (int). Bumped on every mutating
                               write. Not a content fingerprint: it answers "did this
                               artefact change since I last looked?", not "is it the same
                               network as that other artefact?".
``bsb_schema_version``         Version of the bundle layout itself, so future BSB
                               versions can read / write / migrate older and newer
                               schemas.
``created_at``                 ISO 8601 UTC timestamp of engine creation.
``bsb_core_version``           ``importlib.metadata.version("bsb-core")`` at creation
                               time (every package and plugin is also in ``plugins``).
``engine_name``                ``"hdf5"`` or ``"fs"``.
``engine_version``             Engine package version at creation time.
``plugins``                    ``{category: {entry_name: {package, version}}}`` enumerated
                               from :func:`bsb.plugins.discover`. Covers
                               ``storage.engines``, ``config.parsers``,
                               ``config.templates``, ``simulation_backends``,
                               ``commands`` and ``options``.
``host``                       Diagnostic, optional: ``{platform, python_version,
                               hostname, user, cwd}`` of the last writer.
``mpi_size``                   Diagnostic, optional: ``comm.get_size()`` of the last
                               writer. Reconstructions can be built in parts, so this
                               is best-effort.
============================== ==============================================================

The bundle is the back-pointer target for simulation result files. Every ``.nio``
:class:`neo:neo.core.Block` annotates ``bsb_provenance.scaffold = {storage_id,
state_id, root}`` (see :ref:`recorder-convention`).

Sub-interfaces
--------------

Beyond the engine object itself, a storage backend supplies a concrete subclass of
each sub-interface it supports (a metadata-only backend may supply only
:class:`FileStore <bsb:bsb.storage.interfaces.FileStore>`). Each subsection links the
abstract class (whose page lists every method signature) and then states the contract
an implementation must honour: what it stores, the data model, which methods are
mandatory, how access is coordinated, and the provenance hooks.

Declaring an implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There is no registry call or decorator. The framework discovers an engine's
implementations by scanning the engine's plugin module for the first class that
subclasses each storage interface (the :class:`Engine
<bsb:bsb.storage.interfaces.Engine>` itself is found the same way). You declare a
sub-interface implementation simply by subclassing the abstract class and exporting
it from your plugin package's top-level namespace, next to a ``StorageNode`` config
node (which is mandatory):

.. code-block:: python

    # my_engine/__init__.py  (the module registered under the bsb.storage.engines entry point)
    from bsb import Engine, StorageNode as IStorageNode
    from bsb import FileStore as IFileStore

    class MyEngine(Engine): ...
    class StorageNode(IStorageNode): ...     # the config node for storage.engine
    class FileStore(IFileStore): ...         # discovered as this engine's FileStore

    # Re-export from submodules so the scan finds them at the package top level:
    # from .placement_set import PlacementSet
    # from .connectivity_set import ConnectivitySet
    # from .morphology_repository import MorphologyRepository

A sub-interface you do not subclass resolves to a ``NotSupported`` stand-in that
raises on use; that is how a metadata-only engine omits placement and connectivity.

Two of the four sub-interfaces declare an ``engine_key`` on the abstract class
(:class:`FileStore <bsb:bsb.storage.interfaces.FileStore>` keys ``files``,
:class:`MorphologyRepository <bsb:bsb.storage.interfaces.MorphologyRepository>` keys
``morphologies``). For those, the :class:`Storage <bsb:bsb.storage.Storage>` factory
instantiates your subclass once and binds the singleton on the engine under that key,
so ``engine.files`` and ``engine.morphologies`` are ready to use. The other two have
no singleton (there is one placement set per cell type and one connectivity set per
tag); the engine hands those out through its factory methods, such as
``require_placement_set``, which call your subclass's ``create`` / ``require``.

Two cross-cutting rules apply to all four:

* Ordinary reads and data writes are *individual* actions. The engine serialises
  concurrent access with a lock, so any single rank may read or write on its own;
  placement and connectivity strategies routinely write their chunk's data from one
  rank. Only a handful of engine-level operations are *collective* and must be
  entered from every rank under MPI (they barrier internally):
  :meth:`create <bsb:bsb.storage.interfaces.Engine.create>`,
  :meth:`move <bsb:bsb.storage.interfaces.Engine.move>`,
  :meth:`copy <bsb:bsb.storage.interfaces.Engine.copy>`,
  :meth:`remove <bsb:bsb.storage.interfaces.Engine.remove>`,
  :meth:`clear_placement <bsb:bsb.storage.interfaces.Engine.clear_placement>`,
  :meth:`clear_connectivity <bsb:bsb.storage.interfaces.Engine.clear_connectivity>`,
  and
  :meth:`store_active_config <bsb:bsb.storage.interfaces.FileStore.store_active_config>`.
  Those may not be called from component code.
* Every write path must leave the provenance counters consistent by calling
  :meth:`_bump_state <bsb:bsb.storage.interfaces.Engine._bump_state>` on the engine
  (directly, or via the in-handle equivalent) before the lock is released.

FileStore
^^^^^^^^^

**Class:** :class:`FileStore <bsb:bsb.storage.interfaces.FileStore>`

A key-value store of opaque blobs. Each entry is a ``(content, meta)`` pair filed
under a string id. The framework uses it for the active configuration JSON and for
every file or data dependency declared by a component: morphology sources, atlases,
NRRD volumes, and so on. Components SHOULD declare every external file they depend on
so the file store can absorb it, leaving a single self-contained reconstruction file
that carries everything needed to rebuild the network with no loose external paths.
This is the smallest sub-interface and the only one the
:class:`fs <bsb:bsb.storage.fs.FileSystemEngine>` engine implements, which makes it
the best place to start a new backend.

An entry's ``meta`` is a free dict, but three keys are conventional and the
framework relies on them: ``mtime`` (write timestamp), ``encoding`` (text codec, or
absent for binary), and ``active_config`` (the boolean flag marking the live
configuration).

Mandatory methods:

* reads:
  :meth:`all <bsb:bsb.storage.interfaces.FileStore.all>`,
  :meth:`has <bsb:bsb.storage.interfaces.FileStore.has>`,
  :meth:`load <bsb:bsb.storage.interfaces.FileStore.load>`,
  :meth:`get_meta <bsb:bsb.storage.interfaces.FileStore.get_meta>`,
  :meth:`get_mtime <bsb:bsb.storage.interfaces.FileStore.get_mtime>`,
  :meth:`get_encoding <bsb:bsb.storage.interfaces.FileStore.get_encoding>`;
* writes:
  :meth:`store <bsb:bsb.storage.interfaces.FileStore.store>`,
  :meth:`remove <bsb:bsb.storage.interfaces.FileStore.remove>`;
* active configuration:
  :meth:`store_active_config <bsb:bsb.storage.interfaces.FileStore.store_active_config>`,
  :meth:`load_active_config <bsb:bsb.storage.interfaces.FileStore.load_active_config>`.

The lookup helpers
(:meth:`get <bsb:bsb.storage.interfaces.FileStore.get>`,
:meth:`find_files <bsb:bsb.storage.interfaces.FileStore.find_files>`,
:meth:`find_file <bsb:bsb.storage.interfaces.FileStore.find_file>`,
:meth:`find_id <bsb:bsb.storage.interfaces.FileStore.find_id>`,
:meth:`find_meta <bsb:bsb.storage.interfaces.FileStore.find_meta>`) are concrete on
the ABC, built on :meth:`all <bsb:bsb.storage.interfaces.FileStore.all>`.

``store(content, id=None, meta=None, encoding=None, overwrite=False) -> str``
    The single write primitive. Steps an implementation must perform:

    #. If ``id`` is ``None``, mint one with :func:`uuid4 <uuid.uuid4>` and use it as
       the return value.
    #. Normalise content. A ``str`` is encoded to ``bytes`` (default ``utf-8``,
       unless ``encoding`` overrides it); ``bytes`` are stored verbatim with
       ``encoding`` left ``None``. Record the chosen ``encoding`` in the entry so
       :meth:`load <bsb:bsb.storage.interfaces.FileStore.load>` can decode it back.
    #. If ``overwrite`` is false and the id already exists, raise
       :class:`FileExistsError`. If it is true, replace the existing entry.
    #. Stamp ``meta["mtime"]`` with the current time and, for provenance, a
       ``content_sha256`` of the bytes and a ``producer`` (``{"package", "version"}``)
       describing who wrote the file.
    #. Persist content and meta, then bump engine state.

    A minimal filesystem implementation looks like this:

    .. code-block:: python

        import hashlib, json, time, uuid

        def store(self, content, id=None, meta=None, encoding=None, overwrite=False):
            if isinstance(content, str):
                encoding = encoding or "utf-8"
                content = content.encode(encoding)
            id = id or str(uuid.uuid4())
            meta = {**(meta or {})}
            if not overwrite and self.has(id):
                raise FileExistsError(f"'{id}' already in the store")
            meta.setdefault("content_sha256", hashlib.sha256(content).hexdigest())
            self._write_blob(id, content)
            self._write_meta(id, {"meta": meta, "mtime": time.time(), "encoding": encoding})
            self._engine._bump_state()
            return id

``load(id) -> tuple[str | bytes, dict]``
    Return ``(content, meta)``. Decode the content with the stored ``encoding`` (so
    text round-trips as ``str``); return raw ``bytes`` when ``encoding`` is ``None``.
    The second element is the user ``meta`` mapping, not the internal record. Raise
    :class:`FileNotFoundError` for an unknown id.

``remove(id)``
    Delete the entry (both content and meta) and bump engine state. Raise
    :class:`FileNotFoundError` for an unknown id.

``all() -> dict[str, dict]``
    Return ``{id: meta}`` for every entry. This is the workhorse the concrete
    ``find_*`` helpers iterate, so keep it cheap; return only the meta, never the
    content.

``has(id) -> bool``
    Whether an entry with that id exists. Must not raise for a missing id.

``get_meta(id) -> dict`` / ``get_mtime(id)`` / ``get_encoding(id)``
    Targeted accessors for one entry: the user meta mapping, the numeric write
    timestamp, and the text codec (or ``None`` for binary) respectively.

``store_active_config(config) -> str``
    Persist ``config`` as *the* active configuration. There is at most one at a time,
    so first remove any entry whose meta has ``active_config`` set, then
    :meth:`store <bsb:bsb.storage.interfaces.FileStore.store>` ``json.dumps(config.__tree__())``
    with ``meta={"active_config": True, "producer": {...}}``. Returns the new id.
    This call is collective under MPI; the reference engines do the actual write on
    rank 0 and broadcast the id.

``load_active_config() -> Configuration``
    Find the entry flagged ``active_config`` (the ``find_meta("active_config", True)``
    helper does this), parse its JSON back into a
    :class:`Configuration <bsb:bsb.config.Configuration>` with
    ``Configuration(**tree)``, re-attach the stored meta as ``cfg._meta``, and return
    it. Raise
    :class:`MissingActiveConfigError <bsb:bsb.exceptions.MissingActiveConfigError>`
    when no entry is flagged. Parse with :func:`json.loads`, never ``eval``: stored
    files may come from untrusted sources.

PlacementSet
^^^^^^^^^^^^

**Class:** :class:`PlacementSet <bsb:bsb.storage.interfaces.PlacementSet>`

Stores placement data for a cell type. Its identifier is its ``tag``; by convention
a cell type has one placement set whose tag is the cell-type name, but neither the
one-set-per-type nor the tag-equals-name correspondence is enforced. Data is
partitioned into :class:`chunks <bsb:bsb.storage._chunks.Chunk>` (spatial buckets). A
cell's placement-set id is its rank across all chunks taken in sorted chunk order, so
the engine derives ids from the per-chunk counts rather than storing them.

Per cell the set holds: a position (``N×3`` float), a rotation (``N×3``), a
morphology index (into the set's morphology loaders), an encoded label set, and any
number of named ``additional`` arrays.

Mandatory methods group into:

* construction and existence:
  :meth:`create <bsb:bsb.storage.interfaces.PlacementSet.create>`,
  :meth:`exists <bsb:bsb.storage.interfaces.PlacementSet.exists>`, ``__init__``,
  ``__len__`` (``require`` is concrete on the ABC);
* reads:
  :meth:`load_positions <bsb:bsb.storage.interfaces.PlacementSet.load_positions>`,
  :meth:`load_rotations <bsb:bsb.storage.interfaces.PlacementSet.load_rotations>`,
  :meth:`load_morphologies <bsb:bsb.storage.interfaces.PlacementSet.load_morphologies>`,
  :meth:`load_additional <bsb:bsb.storage.interfaces.PlacementSet.load_additional>`,
  :meth:`load_ids <bsb:bsb.storage.interfaces.PlacementSet.load_ids>`,
  :meth:`get_all_chunks <bsb:bsb.storage.interfaces.PlacementSet.get_all_chunks>`,
  :meth:`get_chunk_stats <bsb:bsb.storage.interfaces.PlacementSet.get_chunk_stats>`,
  ``__iter__``;
* writes:
  :meth:`append_data <bsb:bsb.storage.interfaces.PlacementSet.append_data>`,
  :meth:`append_additional <bsb:bsb.storage.interfaces.PlacementSet.append_additional>`,
  :meth:`clear <bsb:bsb.storage.interfaces.PlacementSet.clear>`;
* scoping and labels:
  :meth:`chunk_context <bsb:bsb.storage.interfaces.PlacementSet.chunk_context>`,
  :meth:`set_chunk_filter <bsb:bsb.storage.interfaces.PlacementSet.set_chunk_filter>`,
  :meth:`set_morphology_label_filter <bsb:bsb.storage.interfaces.PlacementSet.set_morphology_label_filter>`,
  :meth:`label <bsb:bsb.storage.interfaces.PlacementSet.label>`,
  :meth:`label_by_mask <bsb:bsb.storage.interfaces.PlacementSet.label_by_mask>`,
  :meth:`remove_labels <bsb:bsb.storage.interfaces.PlacementSet.remove_labels>`,
  :meth:`remove_labels_by_mask <bsb:bsb.storage.interfaces.PlacementSet.remove_labels_by_mask>`,
  :meth:`get_label_mask <bsb:bsb.storage.interfaces.PlacementSet.get_label_mask>`,
  :meth:`get_labelled <bsb:bsb.storage.interfaces.PlacementSet.get_labelled>`,
  :meth:`get_unique_labels <bsb:bsb.storage.interfaces.PlacementSet.get_unique_labels>`.

``count_morphologies``, ``load_boxes``, ``load_box_tree``,
:meth:`set_label_filter <bsb:bsb.storage.interfaces.PlacementSet.set_label_filter>`
and ``get_label_filter`` are concrete on the ABC.

The chunk model
"""""""""""""""

Each :meth:`append_data <bsb:bsb.storage.interfaces.PlacementSet.append_data>` call
targets a single :class:`chunk <bsb:bsb.storage._chunks.Chunk>`, but you may create
new chunks and append to existing ones in any order. A chunk is a fixed-size box of
space identified by its integer key; placement strategies fill chunks in parallel,
each rank owning a subset. An implementation therefore stores every per-cell dataset
*partitioned by chunk*, and never assumes a single contiguous array.

A cell's **placement-set id** is not stored. It is defined as the cell's rank when
chunks are concatenated in sorted key order: all cells of the lowest chunk first
(:math:`0 \ldots n_0 - 1`), then the next chunk
(:math:`n_0 \ldots n_0 + n_1 - 1`), and so on. Every read that returns ids (or that a
caller will index by id) must use this ordering, which is why
:meth:`get_chunk_stats <bsb:bsb.storage.interfaces.PlacementSet.get_chunk_stats>`
(the ``{chunk_key: count}`` map) is load-bearing: it is the source of truth that
turns chunk-local rows into global ids, and connectivity relies on it to offset its
location matrices.

Writing data
""""""""""""

``append_data(chunk, positions=None, morphologies=None, rotations=None, additional=None, count=None)``
    Append cells to one chunk. The optional arguments fill datasets left to right and
    are positionally dependent: to pass ``morphologies`` you must also pass
    ``positions``; to pass ``rotations`` you must pass at least ``positions``.
    ``count`` is the entity escape hatch: it creates ``count`` position-less cells and
    is mutually exclusive with ``positions``/``morphologies``/``rotations``. After
    writing the datasets, update this set's per-chunk counts and total length, then
    bump engine state. Sketch:

    .. code-block:: python

        def append_data(self, chunk, positions=None, morphologies=None,
                        rotations=None, additional=None, count=None):
            n = count if count is not None else len(positions)
            if positions is not None:
                self._append(chunk, "position", positions)
            if morphologies is not None:        # merges loaders, stores indices
                self._append_morphologies(chunk, morphologies)
            if rotations is not None:
                self._append(chunk, "rotation", rotations)
            for key, data in (additional or {}).items():
                self.append_additional(key, chunk, data)
            self._track_add(chunk, n)           # update stats + len, bump state

``append_additional(name, chunk, data)``
    Append ``len(data)`` rows to the chunk's array stored under ``name``, creating it
    on first use. It appends, never overwrites: call it with each batch's rows
    alongside the matching
    :meth:`append_data <bsb:bsb.storage.interfaces.PlacementSet.append_data>` so the
    named array grows in lockstep with the chunk's cells (append N positions then N
    rows, later M positions then M rows). Use it for arbitrary per-cell user data
    that should live and be filtered alongside the placement.

``clear(chunks=None)``
    Drop all data (or only the given chunks), decrementing the chunk counts you track
    so :meth:`get_chunk_stats <bsb:bsb.storage.interfaces.PlacementSet.get_chunk_stats>`
    stays exact. Bump engine state.

Reading data
""""""""""""

``load_positions()`` / ``load_rotations()`` / ``load_additional(key=None)``
    Return the concatenated ``N×3`` positions, a
    :class:`RotationSet <bsb:bsb.morphologies.RotationSet>`, and the named additional
    array(s), in placement-set id order. When a chunk or label filter is active they
    return only the matching rows. ``load_rotations`` and ``load_morphologies`` raise
    :class:`DatasetNotFoundError <bsb:bsb.exceptions.DatasetNotFoundError>` when the
    data is absent (unless ``allow_empty`` is set).

``load_morphologies(allow_empty=False)``
    Return a :class:`MorphologySet <bsb:bsb.morphologies.MorphologySet>` pairing the
    set's loaders with the per-cell morphology index. The loaders are obtained from
    the engine's
    :class:`MorphologyRepository <bsb:bsb.storage.interfaces.MorphologyRepository>`,
    and the per-cell dataset holds integer indices into that loader list, so storing
    morphologies means storing names plus indices, not duplicating geometry per cell.

``load_ids()``
    Return the global ids in scope as a flat array, derived from the chunk counts (and
    masked by the label filter when set). A caller uses these to line recorded data
    back up with cells.

``get_all_chunks()`` / ``get_chunk_stats()``
    The chunks that hold data, and the ``{chunk_key: count}`` map. Keep
    ``get_chunk_stats`` exact: id derivation and connectivity scoping both depend on
    it.

Scope filters
"""""""""""""

Filters narrow a set in place: while one is active, ``__len__`` and every ``load_*``
reflect only the matching cells, and a freshly loaded set has none set.

``chunk_context(chunks)``
    A context manager that restricts the set to ``chunks`` for the duration of a
    ``with`` block. Use it internally to read one chunk's slice without mutating the
    persistent filter.

``set_chunk_filter(chunks)``
    Persistently restrict reads to the given chunks until changed.

``set_morphology_label_filter(morphology_labels)``
    Restrict the *sub-cellular* scope: morphologies returned by
    :meth:`load_morphologies <bsb:bsb.storage.interfaces.PlacementSet.load_morphologies>`
    will be filtered to these labels.
    :meth:`set_label_filter <bsb:bsb.storage.interfaces.PlacementSet.set_label_filter>`
    and ``get_label_filter`` (cell-level, concrete on the ABC) cover the cell scope.

Labels
""""""

Each cell carries an encoded label set. The label methods read and mutate it:

``label(labels, cells)`` / ``label_by_mask(labels, mask)``
    Add ``labels`` to the cells named by id, or by a boolean mask the length of the
    set. Validate that ids are in range / the mask fits, raising
    :class:`LabellingError <bsb:bsb.exceptions.LabellingError>` otherwise.

``remove_labels(labels, cells)`` / ``remove_labels_by_mask(labels, mask)``
    The inverse: strip ``labels`` from the selected cells.

``get_label_mask(labels=None)`` / ``get_labelled(labels=None)`` / ``get_unique_labels()``
    Query: a boolean mask for cells carrying ``labels``, their ids, and the set of all
    labels in use. Passing an empty list selects unlabelled cells.

ConnectivitySet
^^^^^^^^^^^^^^^

**Class:** :class:`ConnectivitySet <bsb:bsb.storage.interfaces.ConnectivitySet>`

Stores the connections between a presynaptic and a postsynaptic cell type, written
once from each perspective (``inc`` and ``out``) and partitioned per chunk so that
incoming and outgoing queries are both cheap. The engine must set the class
attributes ``tag``, ``pre_type_name``, ``post_type_name``, ``pre_type`` and
``post_type`` on every instance.

A connection is a pair of locations. A location is a row ``[cell_id, branch_id,
point_id]``; point-neuron connections use ``-1`` for the branch and point columns.
Locations are interpreted in one of two frames:

* :meth:`connect <bsb:bsb.storage.interfaces.ConnectivitySet.connect>` takes
  placement-set-scoped cell ids (the rank within the whole set);
* :meth:`chunk_connect <bsb:bsb.storage.interfaces.ConnectivitySet.chunk_connect>`
  takes chunk-relative cell ids (the rank within the named chunk).

Mandatory methods:

* construction and existence:
  :meth:`create <bsb:bsb.storage.interfaces.ConnectivitySet.create>`,
  :meth:`exists <bsb:bsb.storage.interfaces.ConnectivitySet.exists>`,
  :meth:`get_tags <bsb:bsb.storage.interfaces.ConnectivitySet.get_tags>`;
* writes:
  :meth:`connect <bsb:bsb.storage.interfaces.ConnectivitySet.connect>`,
  :meth:`chunk_connect <bsb:bsb.storage.interfaces.ConnectivitySet.chunk_connect>`,
  :meth:`clear <bsb:bsb.storage.interfaces.ConnectivitySet.clear>`;
* reads:
  :meth:`get_local_chunks <bsb:bsb.storage.interfaces.ConnectivitySet.get_local_chunks>`,
  :meth:`get_global_chunks <bsb:bsb.storage.interfaces.ConnectivitySet.get_global_chunks>`,
  :meth:`flat_iter_connections <bsb:bsb.storage.interfaces.ConnectivitySet.flat_iter_connections>`,
  :meth:`nested_iter_connections <bsb:bsb.storage.interfaces.ConnectivitySet.nested_iter_connections>`,
  :meth:`load_block_connections <bsb:bsb.storage.interfaces.ConnectivitySet.load_block_connections>`,
  :meth:`load_local_connections <bsb:bsb.storage.interfaces.ConnectivitySet.load_local_connections>`.

``require`` and
:meth:`load_connections <bsb:bsb.storage.interfaces.ConnectivitySet.load_connections>`
(which returns a
:class:`ConnectivityIterator <bsb:bsb.storage.interfaces.ConnectivityIterator>`) are
concrete on the ABC.

The location and direction model
""""""""""""""""""""""""""""""""

``src_locs`` and ``dest_locs`` are equal-length ``N×3`` integer matrices: one row
per connection, columns ``[cell_id, branch_id, point_id]``. ``src`` is presynaptic,
``dest`` is postsynaptic. A point-neuron connection sets branch and point to ``-1``;
a 1-D id vector is broadcast to that shape for you by the reference helper.

Connections are stored **twice**, once per direction, so that both "who do I send
to" and "who sends to me" are local reads:

* ``out``: keyed by the presynaptic (local) chunk, pointing at postsynaptic (global)
  chunks;
* ``inc``: keyed by the postsynaptic (local) chunk, pointing at presynaptic (global)
  chunks.

"Local" is the chunk you index by; "global" is the chunk on the other end of the
connection. Writing one batch of connections means appending to both an ``out`` block
and an ``inc`` block.

Writing connections
"""""""""""""""""""

``connect(pre_set, post_set, src_locs, dest_locs)``
    The high-level entry point. ``src_locs`` and ``dest_locs`` carry
    placement-set-scoped cell ids (rank within the whole set). It must: resolve any
    active label filter on ``pre_set`` / ``post_set`` (translating filtered ids back
    to stored ids), apply morphology back-mapping where the sets require it, then
    demultiplex the rows per ``(pre_chunk, post_chunk)`` pair and hand each block to
    ``chunk_connect``. An engine that implements ``chunk_connect`` plus the iterators
    gets ``connect`` for free by reusing the reference demultiplexer; only override it
    if your backend can route locations to chunks more cheaply.

``chunk_connect(src_chunk, dst_chunk, src_locs, dst_locs)``
    The low-level primitive. Here the cell ids are chunk-relative (rank within the
    named chunk). Append ``src_locs`` to the ``out`` block of ``src_chunk`` (global
    ``dst_chunk``) and to the ``inc`` block of ``dst_chunk`` (global ``src_chunk``),
    then update the per-direction counts and bump engine state. ``src_locs`` and
    ``dst_locs`` must be the same length.

``clear(chunks=None)``
    Drop the connectivity (or only the given chunks) from both directions and reset
    the counts. Bump engine state.

Reading connections
"""""""""""""""""""

``get_local_chunks(direction)``
    List the local chunks that hold data in ``"inc"`` or ``"out"``.

``get_global_chunks(direction, local_)``
    List the global chunks reachable from a given local chunk in that direction.

``load_block_connections(direction, local_, global_)``
    Return the ``(local_locs, global_locs)`` pair for one ``(local, global)`` block.
    This is the leaf read the iterators are built on; an empty block returns two
    ``(0, 3)`` arrays rather than raising.

``load_local_connections(direction, local_)``
    Return all connections of one local chunk as ``(local_locs, global_chunk_ids,
    global_locs)``, where the middle array tags each global row with its chunk so the
    caller can resolve cross-chunk ids.

``flat_iter_connections(direction=None, local_=None, global_=None)`` / ``nested_iter_connections(...)``
    Iterate the blocks. The flat form yields ``(direction, local_chunk, global_chunk,
    data)`` tuples; the nested form yields nested iterators for hand-written loops.
    Omitting an argument iterates that axis; passing one pins it. The concrete
    :meth:`load_connections <bsb:bsb.storage.interfaces.ConnectivitySet.load_connections>`
    wraps these into a
    :class:`ConnectivityIterator <bsb:bsb.storage.interfaces.ConnectivityIterator>`
    that applies the placement-set chunk offsets, so most callers never touch the raw
    blocks:

    .. code-block:: python

        cs = scaffold.get_connectivity_set("A_to_B")
        for pre_loc, post_loc in cs.load_connections():
            # pre_loc / post_loc are [cell_id, branch_id, point_id], ids global to the set
            ...

MorphologyRepository
^^^^^^^^^^^^^^^^^^^^

**Class:** :class:`MorphologyRepository <bsb:bsb.storage.interfaces.MorphologyRepository>`

Stores morphologies and their metadata, content-addressed by a hash kept in each
morphology's meta. PlacementSets reference its loaders by name.

Mandatory methods:

* reads:
  :meth:`all <bsb:bsb.storage.interfaces.MorphologyRepository.all>`,
  :meth:`select <bsb:bsb.storage.interfaces.MorphologyRepository.select>`,
  :meth:`has <bsb:bsb.storage.interfaces.MorphologyRepository.has>`,
  :meth:`preload <bsb:bsb.storage.interfaces.MorphologyRepository.preload>`,
  :meth:`load <bsb:bsb.storage.interfaces.MorphologyRepository.load>`,
  :meth:`get_meta <bsb:bsb.storage.interfaces.MorphologyRepository.get_meta>`,
  :meth:`get_all_meta <bsb:bsb.storage.interfaces.MorphologyRepository.get_all_meta>`;
* writes:
  :meth:`save <bsb:bsb.storage.interfaces.MorphologyRepository.save>`,
  :meth:`set_all_meta <bsb:bsb.storage.interfaces.MorphologyRepository.set_all_meta>`,
  :meth:`update_all_meta <bsb:bsb.storage.interfaces.MorphologyRepository.update_all_meta>`.

``__contains__`` and
:meth:`list <bsb:bsb.storage.interfaces.MorphologyRepository.list>` are concrete on
the ABC.

A morphology has two parts an implementation must round-trip: its **geometry** (the
branch tree of points, radii, per-point labels and properties) and its **meta** (a
free dict that carries at least the content ``hash``). The two are queried
separately because most of the framework only needs names and meta, and loading
geometry is expensive. That split is why there is both a lazy
:class:`StoredMorphology <bsb:bsb.storage.interfaces.StoredMorphology>` (a loader
plus meta) and an eager
:class:`Morphology <bsb:bsb.morphologies.Morphology>`.

Writing
"""""""

``save(name, morphology, overwrite=False)``
    Persist a :class:`Morphology <bsb:bsb.morphologies.Morphology>` under ``name``.
    Raise :class:`MorphologyRepositoryError
    <bsb:bsb.exceptions.MorphologyRepositoryError>` if the name exists and
    ``overwrite`` is false. Serialise the branch tree to your backend and write the
    morphology's meta, which must include the ``hash`` so a
    :class:`PlacementSet <bsb:bsb.storage.interfaces.PlacementSet>` write can read it
    back into ``morphology_hashes``.

``set_all_meta(all_meta)`` / ``update_all_meta(meta)``
    Replace, or merge into, the ``{name: meta}`` map for the whole repository. Used to
    rewrite metadata without touching geometry.

Reading
"""""""

``all()``
    Return a :class:`StoredMorphology <bsb:bsb.storage.interfaces.StoredMorphology>`
    for every stored morphology, preloaded from the meta map (no geometry read).

``has(name)``
    Whether a morphology of that name exists. Backs the concrete ``__contains__``.

``preload(name)``
    Return a lazy
    :class:`StoredMorphology <bsb:bsb.storage.interfaces.StoredMorphology>`: its meta
    is read now, its geometry only when the caller calls ``.load()`` on it. This is
    what :meth:`PlacementSet.load_morphologies
    <bsb:bsb.storage.interfaces.PlacementSet.load_morphologies>` collects, so it must
    be cheap.

``load(name)``
    Read the geometry and return a fully constructed
    :class:`Morphology <bsb:bsb.morphologies.Morphology>`: rebuild the branch tree
    from your stored point, radius, label and property arrays and attach the meta.

``get_meta(name)`` / ``get_all_meta()``
    The meta dict for one morphology, or the whole ``{name: meta}`` map. Raise
    :class:`MissingMorphologyError <bsb:bsb.exceptions.MissingMorphologyError>` for an
    unknown name.

``select(*selectors)``
    Run :class:`MorphologySelector
    <bsb:bsb.morphologies.selector.MorphologySelector>` objects against ``all()`` and
    return the matching stored morphologies. Call each selector's ``validate`` once
    before filtering, so a selector that names a missing morphology fails loudly:

    .. code-block:: python

        def select(self, *selectors):
            if not selectors:
                return []
            loaders = self.all()
            picked = []
            for selector in selectors:
                selector.validate(loaders)
                picked.extend(filter(selector.pick, loaders))
            return picked

Keeping provenance current
--------------------------

Every write path across the sub-interfaces keeps the
:ref:`provenance bundle <storage-engine-contract>` in step with the data:

* placement writes (``append_data``, ``append_additional``, the ``label*`` methods,
  ``clear``) bump ``revision`` on the placement set and refresh
  ``morphology_hashes`` when morphology data changed;
* connectivity writes (``connect``, ``chunk_connect``, ``clear``) bump ``revision``
  on the connectivity set;
* file writes (``store``, ``remove``, ``store_active_config``) record
  ``content_sha256`` and ``producer`` per file;
* all of them bump the engine's ``state_id`` (the cross-cutting
  :meth:`_bump_state <bsb:bsb.storage.interfaces.Engine._bump_state>` rule).

**Backfilling a storage that lacks provenance.** When an engine opens a root with no
provenance bundle (one written before the engine grew provenance support, or by a
third-party tool), it backfills one: the ``_upgrade_if_needed`` step stamps a fresh
bundle transparently and emits a single
:class:`BsbProvenanceUpgradeWarning
<bsb:bsb.exceptions.BsbProvenanceUpgradeWarning>`. Read-only opens skip the backfill;
:attr:`scaffold.storage_id <bsb:bsb.core.Scaffold.storage_id>` and
:attr:`scaffold.state_id <bsb:bsb.core.Scaffold.state_id>` are then ``None``, and any
simulation result written against that scaffold records ``"storage_id": None`` in its
back-pointer. To force the backfill, reopen writable and trigger any mutation.

Reference walkthrough
---------------------

For a worked example, follow the
:class:`HDF5Engine <bsb_hdf5:bsb_hdf5.HDF5Engine>` implementation (full PS/CS
support) and the :class:`FileSystemEngine <bsb:bsb.storage.fs.FileSystemEngine>`
implementation (metadata-only, atomic writes via tmpfile and :func:`os.replace`).
Both reuse :func:`build_root_metadata <bsb:bsb.storage.provenance.build_root_metadata>`,
:func:`iso_now <bsb:bsb.storage.provenance.iso_now>`, and the shared plugin and host collectors
so the bundle stays consistent across engines.
