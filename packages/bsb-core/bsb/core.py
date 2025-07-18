from __future__ import annotations

import contextlib
import itertools
import os
import sys
import time
import typing

import numpy as np

from ._util import obj_str_insert
from .config._config import Configuration
from .connectivity import ConnectionStrategy
from .exceptions import (
    ConfigurationSyncError,
    DatasetNotFoundError,
    InputError,
    MissingActiveConfigError,
    NodeNotFoundError,
    RedoError,
)
from .placement import PlacementStrategy
from .profiling import meter
from .reporting import report
from .services import JobPool
from .services._pool_listeners import NonTTYTerminalListener, TTYTerminalListener
from .services.mpi import MPIService
from .services.pool import Job, Workflow
from .simulation import get_simulation_adapter
from .storage import Storage, open_storage
from .storage._chunks import Chunk

if typing.TYPE_CHECKING:
    from .cell_types import CellType
    from .config._config import NetworkNode as Network
    from .postprocessing import AfterConnectivityHook, AfterPlacementHook
    from .simulation.simulation import Simulation
    from .storage.interfaces import (
        ConnectivitySet,
        FileStore,
        MorphologyRepository,
        PlacementSet,
    )
    from .topology import Partition, Region


@meter()
def from_storage(root, comm=None):
    """
    Load :class:`bsb.core.Scaffold` from a storage object.

    :param root: Root (usually path) pointing to the storage object.
    :param mpi4py.MPI.Comm comm: MPI communicator that shares control
      over the Storage.
    :returns: A network scaffold
    :rtype: :class:`bsb.core.Scaffold`
    """
    return open_storage(root, comm).load()


_cfg_props = (
    "network",
    "regions",
    "partitions",
    "cell_types",
    "placement",
    "after_placement",
    "connectivity",
    "after_connectivity",
    "simulations",
)


def _config_property(name):
    def fget(self):
        return getattr(self.configuration, name)

    def fset(self, value):
        setattr(self.configuration, name, value)

    prop = property(fget)
    return prop.setter(fset)


def _bad_flag(flag: bool):
    return flag is not None and bool(flag) is not flag


class Scaffold:
    """
    This is the main object of the bsb package, it represents a network and puts together
    all the pieces that make up the model description such as the
    :class:`~.config.Configuration` with the technical side like the
    :class:`~.storage.Storage`.
    """

    network: Network
    regions: dict[str, Region]
    partitions: dict[str, Partition]
    cell_types: dict[str, CellType]
    placement: dict[str, PlacementStrategy]
    after_placement: dict[str, AfterPlacementHook]
    connectivity: dict[str, ConnectionStrategy]
    after_connectivity: dict[str, AfterConnectivityHook]
    simulations: dict[str, Simulation]

    def __init__(self, config=None, storage=None, clear=False, comm=None):
        """
        Bootstraps a network object.

        :param config: The configuration to use for this network. If it is omitted the
          :external:ref:`bsb.default configuration <default-config>` is used.
        :type config: :class:`~.config.Configuration`
        :param storage: The storage to use to read and write data for this network. If it
          is omitted the configuration's ``Storage`` node is used to construct one.
        :type storage: :class:`~.storage.Storage`
        :param clear: Start with a new network, clearing any previously stored information
        :type clear: bool
        :param comm: MPI communicator that shares control over the Storage.
        :type comm: mpi4py.MPI.Comm
        :returns: A network object
        :rtype: :class:`~.core.Scaffold`
        """
        self._pool_cache: dict[int, typing.Callable[[], None]] = {}
        self._pool_listeners: list[tuple[typing.Callable[[list[Job]], None], float]] = []
        self._configuration = None
        self._storage = None
        self._comm = MPIService(comm)
        self._bootstrap(config, storage, clear=clear)

    def __contains__(self, component):
        return getattr(component, "scaffold", None) is self

    @obj_str_insert
    def __repr__(self):
        file = os.path.abspath(self.storage.root)
        cells_placed = len(self.cell_types)
        n_types = len(self.connectivity)
        return f"'{file}' with {cells_placed} cell types, and {n_types} connection_types"

    def is_main_process(self) -> bool:
        return not self._comm.get_rank()

    def is_worker_process(self) -> bool:
        return bool(self._comm.get_rank())

    def _bootstrap(self, config, storage, clear=False):
        # No config object given, traverse config cascade.
        if config is None:
            # Try loading the storage's active config
            if storage is not None:
                with contextlib.suppress(MissingActiveConfigError):
                    config = storage.load_active_config()

            # No luck? Try loading the project configuration
            if config is None:
                import bsb.options

                path = bsb.options.config
                if path and os.path.exists(path):
                    with open(path) as f:
                        config = bsb.config.parse_configuration_file(f, path=path)

            # Still nothing? Use the default configuration
            if config is None:
                config = Configuration.default()

        if not storage:
            # No storage given, create one.
            report("Creating storage from config.", level=4)
            storage = Storage(
                config.storage.engine,
                config.storage.root,
                self._comm.get_communicator(),
            )
        else:
            # Override MPI comm of storage to match the scaffold's
            storage._comm = self._comm
        if clear:
            # Storage given, but asked to clear it before use.
            storage.remove()
            storage.create()
        # Synchronize the scaffold, config and storage objects for use together
        self._configuration = config
        # Make sure the storage config node reflects the storage we are using
        config._update_storage_node(storage)
        # Give the scaffold access to the uninitialized storage object (for use during
        # config bootstrapping).
        self._storage = storage
        # First, the scaffold is passed to each config node, and their boot methods called
        self._configuration._bootstrap(self)
        # Then, `storage` is initialized for the scaffold, and `config` is stored (happens
        # inside the `storage` property).
        self.storage = storage

    storage_cfg = _config_property("storage")
    for attr in _cfg_props:
        vars()[attr] = _config_property(attr)

    @property
    def configuration(self) -> Configuration:
        return self._configuration

    @configuration.setter
    def configuration(self, cfg: Configuration):
        self._configuration = cfg
        cfg._update_storage_node(self.storage)
        cfg._bootstrap(self)
        self.storage.store_active_config(cfg)

    def sync_config(self):
        import bsb.config

        cfg = None
        try:
            cfg = self.storage.load_active_config()
        except MissingActiveConfigError:
            import bsb.options

            path = bsb.options.config
        else:
            path = cfg._meta.get("path", None)
        if path and os.path.exists(path):
            with open(path) as f:
                cfg = bsb.config.parse_configuration_file(f, path=path)

        if cfg is None:
            raise ConfigurationSyncError("Could not find a configuration to sync")

        self.configuration = cfg

    @property
    def storage(self) -> Storage:
        return self._storage

    @storage.setter
    def storage(self, storage: Storage):
        self._storage = storage
        storage.init(self)

    @property
    def morphologies(self) -> MorphologyRepository:
        return self.storage.morphologies

    @property
    def files(self) -> FileStore:
        return self.storage.files

    def clear(self):
        """
        Clears the storage.

        This deletes any existing network data!
        """
        self.storage.renew(self)

    def clear_placement(self):
        """
        Clears the placement storage.
        """
        self.storage.clear_placement(self)

    def clear_connectivity(self):
        """
        Clears the connectivity storage.
        """
        self.storage.clear_connectivity()

    def resize(self, x=None, y=None, z=None):
        """
        Updates the topology boundary indicators.

        Use before placement, updates only the abstract topology tree, does not rescale,
        prune or otherwise alter already existing placement data.
        """
        from .topology._layout import box_layout

        if x is not None:
            self.network.x = x
        if y is not None:
            self.network.y = y
        if z is not None:
            self.network.z = z
        self.topology.do_layout(
            box_layout(
                self.network.origin,
                np.array(self.network.origin)
                + [self.network.x, self.network.y, self.network.z],
            )
        )

    @meter()
    def run_placement(self, strategies=None, fail_fast=True, pipelines=True):
        """
        Run placement strategies.
        """
        if pipelines:
            self.run_pipelines()
        if strategies is None:
            strategies = set(self.placement.values())
        strategies = PlacementStrategy.sort_deps(strategies)
        with self.create_job_pool(fail_fast=fail_fast) as pool:
            if pool.is_main():

                def scheduler(strategy):
                    strategy.queue(pool, self.network.chunk_size)

                pool.schedule(strategies, scheduler)
            pool.execute()

    @meter()
    def run_connectivity(self, strategies=None, fail_fast=True, pipelines=True):
        """
        Run connection strategies.
        """
        if pipelines:
            self.run_pipelines()
        if strategies is None:
            strategies = set(self.connectivity.values())
        strategies = ConnectionStrategy.sort_deps(strategies)
        with self.create_job_pool(fail_fast=fail_fast) as pool:
            if pool.is_main():
                pool.schedule(strategies)
            pool.execute()

    @meter()
    def run_placement_strategy(self, strategy):
        """
        Run a single placement strategy.
        """
        self.run_placement([strategy])

    @meter()
    def run_after_placement(self, hooks=None, fail_fast=None, pipelines=True):
        """
        Run after placement hooks.
        """
        if hooks is None:
            hooks = set(self.after_placement.values())
        with self.create_job_pool(fail_fast) as pool:
            if pool.is_main():
                pool.schedule(hooks)
            pool.execute()

    @meter()
    def run_after_connectivity(self, hooks=None, fail_fast=None, pipelines=True):
        """
        Run after placement hooks.
        """
        if hooks is None:
            hooks = set(self.after_connectivity.values())
        with self.create_job_pool(fail_fast) as pool:
            if pool.is_main():
                pool.schedule(hooks)
            pool.execute()

    @meter()
    def compile(
        self,
        skip_placement=False,
        skip_connectivity=False,
        skip_after_placement=False,
        skip_after_connectivity=False,
        only=None,
        skip=None,
        clear=False,
        append=False,
        redo=False,
        force=False,
        fail_fast=True,
    ):
        """
        Run reconstruction steps in the scaffold sequence to obtain a full network.
        """
        existed = self.storage.preexisted

        p_strats = [] if skip_placement else self.get_placement(skip=skip, only=only)
        c_strats = (
            [] if skip_connectivity else self.get_connectivity(skip=skip, only=only)
        )
        todo_list_str = ", ".join(s.name for s in itertools.chain(p_strats, c_strats))
        report(f"Compiling the following strategies: {todo_list_str}", level=2)
        if _bad_flag(clear) or _bad_flag(redo) or _bad_flag(append):
            raise InputError(
                "`clear`, `redo` and `append` are strictly boolean flags. "
                "Pass the strategies to run to the skip/only options instead."
            )
        if sum((bool(clear), bool(redo), bool(append))) > 1:
            raise InputError("`clear`, `redo` and `append` are mutually exclusive.")
        if existed:
            if not (clear or append or redo):
                raise FileExistsError(
                    f"The `{self.storage.format}` storage"
                    + f" at `{self.storage.root}` already exists. Either move/delete it,"
                    + " or pass one of the `clear`, `append` or `redo` arguments"
                    + " to pick what to do with the existing data."
                )
            if clear:
                report("Clearing data", level=2)
                # Clear the placement and connectivity data, but leave any cached files
                # and morphologies intact.
                self.clear()
            elif redo:
                # In order to properly redo things, we clear some placement and connection
                # data, but since multiple placement/connection strategies can contribute
                # to the same sets we might be wiping their data too, and they will need
                # to be cleared and reran as well.
                p_strats, c_strats = self._redo_chain(p_strats, c_strats, skip, force)
            # else:
            #   append mode is luckily simpler, just don't clear anything :)

        phases = ["pipelines"]
        if not skip_placement:
            phases.append("placement")
        if not skip_after_placement:
            phases.append("after_placement")
        if not skip_connectivity:
            phases.append("connectivity")
        if not skip_after_connectivity:
            phases.append("after_connectivity")
        self._workflow = Workflow(phases)
        try:
            self.run_pipelines(fail_fast=fail_fast)
            self._workflow.next_phase()
            if not skip_placement:
                placement_todo = ", ".join(s.name for s in p_strats)
                report(f"Starting placement strategies: {placement_todo}", level=2)
                self.run_placement(p_strats, fail_fast=fail_fast, pipelines=False)
                self._workflow.next_phase()
            if not skip_after_placement:
                self.run_after_placement(pipelines=False, fail_fast=fail_fast)
                self._workflow.next_phase()
            if not skip_connectivity:
                connectivity_todo = ", ".join(s.name for s in c_strats)
                report(f"Starting connectivity strategies: {connectivity_todo}", level=2)
                self.run_connectivity(c_strats, fail_fast=fail_fast, pipelines=False)
                self._workflow.next_phase()
            if not skip_after_connectivity:
                self.run_after_connectivity(pipelines=False)
                self._workflow.next_phase()
        finally:
            # After compilation we should flag the storage as having existed before
            # so that the `clear`, `redo` and `append` flags take effect on a second
            # `compile` pass.
            self.storage._preexisted = True
            del self._workflow

    @meter()
    def run_pipelines(self, fail_fast=True, pipelines=None):
        if pipelines is None:
            pipelines = self.get_dependency_pipelines()
        with self.create_job_pool(fail_fast=fail_fast) as pool:
            if pool.is_main():
                pool.schedule(pipelines)
            pool.execute()

    @meter()
    def run_simulation(self, simulation_name: str):
        """
        Run a simulation starting from the default single-instance adapter.

        :param simulation_name: Name of the simulation in the configuration.
        :type simulation_name: str
        """
        simulation = self.get_simulation(simulation_name)
        adapter = get_simulation_adapter(
            simulation.simulator, comm=self._comm.get_communicator()
        )
        return adapter.simulate(simulation)[0]

    def get_simulation(self, sim_name: str) -> Simulation:
        """
        Retrieve the default single-instance adapter for a simulation.
        """
        if sim_name not in self.simulations:
            simstr = ", ".join(f"'{s}'" for s in self.simulations)
            raise NodeNotFoundError(
                f"Unknown simulation '{sim_name}', choose from: {simstr}"
            )
        return self.configuration.simulations[sim_name]

    def place_cells(
        self,
        cell_type,
        positions,
        morphologies=None,
        rotations=None,
        additional=None,
        chunk=None,
    ):
        """
        Place cells inside the scaffold.

        .. code-block:: python

            # Add one granule cell at position 0, 0, 0
            cell_type = scaffold.get_cell_type("granule_cell")
            scaffold.place_cells(cell_type, cell_type.layer_instance, [[0.0, 0.0, 0.0]])

        :param cell_type: The type of the cells to place.
        :type cell_type: ~bsb.cell_types.CellType
        :param positions: A collection of xyz positions to place the cells on.
        :type positions: Any `np.concatenate` type of shape (N, 3).
        """
        if chunk is None:
            chunk = Chunk([0, 0, 0], self.network.chunk_size)
        if hasattr(chunk, "dimensions") and np.any(np.isnan(chunk.dimensions)):
            chunk.dimensions = self.network.chunk_size
        self.get_placement_set(cell_type).append_data(
            chunk,
            positions=positions,
            morphologies=morphologies,
            rotations=rotations,
            additional=additional,
        )

    def create_entities(self, cell_type, count):
        """
        Create entities in the simulation space.

        Entities are different from cells because they have no positional data and
        don't influence the placement step. They do have a representation in the
        connection and simulation step.

        :param cell_type: The cell type of the entities
        :type cell_type: ~bsb.cell_types.CellType
        :param count: Number of entities to place
        :type count: int
        :todo: Allow `additional` data for entities
        """
        if count == 0:
            return
        ps = self.get_placement_set(cell_type)
        # Append entity data to the default chunk 000
        chunk = Chunk([0, 0, 0], self.network.chunk_size)
        ps.append_entities(chunk, count)

    def get_placement(
        self, cell_types=None, skip=None, only=None
    ) -> list[PlacementStrategy]:
        if cell_types is not None:
            cell_types = [
                self.cell_types[ct] if isinstance(ct, str) else ct for ct in cell_types
            ]
        return [
            val
            for key, val in self.placement.items()
            if (cell_types is None or any(ct in cell_types for ct in val.cell_types))
            and (only is None or key in only)
            and (skip is None or key not in skip)
        ]

    def get_placement_of(self, *cell_types):
        """
        Find all the placement strategies that involve the given cell types.

        :param cell_types: Cell types (or their names) of interest.
        :type cell_types: ~bsb.cell_types.CellType | str
        """
        return self.get_placement(cell_types=cell_types)

    def get_placement_set(
        self, type, chunks=None, labels=None, morphology_labels=None
    ) -> PlacementSet:
        """
        Return a cell type's placement set from the output formatter.

        :param type: Cell type name
        :type type: ~bsb.cell_types.CellType | str
        :param chunks: Optionally load a specific list of chunks.
        :type chunks: list[tuple[float, float, float]]
        :param labels: Labels to filter the placement set by.
        :type labels: list[str]
        :param morphology_labels: Subcellular labels to apply to the morphologies.
        :type morphology_labels: list[str]
        :returns: A placement set
        :rtype: :class:`~.storage.interfaces.PlacementSet`
        """
        if isinstance(type, str):
            type = self.cell_types[type]
        return self.storage.get_placement_set(
            type, chunks=chunks, labels=labels, morphology_labels=morphology_labels
        )

    def get_placement_sets(self) -> list[PlacementSet]:
        """
        Return all the placement sets present in the network.

        :rtype: list[~bsb.storage.interfaces.PlacementSet]
        """
        return [cell_type.get_placement_set() for cell_type in self.cell_types.values()]

    def connect_cells(self, pre_set, post_set, src_locs, dest_locs, name):
        """
        Connect cells from a presynaptic placement set to cells of a postsynaptic
        placement set, and into a connectivity set.
        The description of the hemitype (source or target cell population)
        connection location is stored as a list of 3 ids: the cell index
        (in the placement set), morphology branch index, and the morphology branch
        section index. If no morphology is attached to the hemitype,
        then the morphology indexes can be set to -1.

        :param bsb.storage.interfaces.PlacementSet pre_set: presynaptic placement set
        :param bsb.storage.interfaces.PlacementSet post_set: postsynaptic placement set
        :param list[list[int, int, int]] src_locs: list of the presynaptic
          `connection location`.
        :param list[list[int, int, int]] dest_locs: list of the postsynaptic
          `connection location`.
        :param str name: Name to give to the `ConnectivitySet`
        """
        cs = self.require_connectivity_set(pre_set.cell_type, post_set.cell_type, name)
        cs.connect(pre_set, post_set, src_locs, dest_locs)

    def get_connectivity(
        self, anywhere=None, presynaptic=None, postsynaptic=None, skip=None, only=None
    ) -> list[ConnectivitySet]:
        conntype_filtered = self._connectivity_query(
            any_query=set(self._sanitize_ct(anywhere)),
            pre_query=set(self._sanitize_ct(presynaptic)),
            post_query=set(self._sanitize_ct(postsynaptic)),
        )
        return [
            ct
            for ct in conntype_filtered
            if (only is None or ct.name in only) and (skip is None or ct.name not in skip)
        ]

    def get_connectivity_sets(self) -> list[ConnectivitySet]:
        """
        Return all connectivity sets from the output formatter.

        :returns: All connectivity sets
        :rtype: list[:class:`~.storage.interfaces.ConnectivitySet`]
        """
        return [self._load_cs_types(cs) for cs in self.storage.get_connectivity_sets()]

    def require_connectivity_set(self, pre, post, tag=None) -> ConnectivitySet:
        return self._load_cs_types(
            self.storage.require_connectivity_set(pre, post, tag), pre, post
        )

    def get_connectivity_set(self, tag=None, pre=None, post=None) -> ConnectivitySet:
        """
        Return a connectivity set from its name according to the output formatter. The
        name can be specified directly with tag or with deduced from pre and post if there
        is only one connectivity set matching this pair.

        :param tag: Unique identifier of the connectivity set in the output formatter
        :type tag: str
        :param pre: Presynaptic cell type
        :type pre: ~bsb.cell_types.CellType
        :param post: Postsynaptic cell type
        :type post: ~bsb.cell_types.CellType
        :returns: A connectivity set
        :rtype: :class:`~.storage.interfaces.ConnectivitySet`
        """
        if tag is None:
            try:
                tag = f"{pre.name}_to_{post.name}"
            except Exception:
                raise ValueError(
                    "Supply either `tag` or a valid pre and post cell type."
                ) from None
        return self._load_cs_types(self.storage.get_connectivity_set(tag), pre, post)

    def get_cell_types(self) -> list[CellType]:
        """
        Return a list of all cell types in the network.
        """
        return [*self.configuration.cell_types.values()]

    def merge(self, other, label=None):
        raise NotImplementedError("Revisit: merge CT, PS & CS, done?")

    def _sanitize_ct(self, seq_str_or_none):
        if seq_str_or_none is None:
            return []
        try:
            if isinstance(seq_str_or_none, str):
                return [self.cell_types[seq_str_or_none]]
            return [
                self.cell_types[s] if isinstance(s, str) else s for s in seq_str_or_none
            ]
        except KeyError as e:
            raise NodeNotFoundError(f"Cell type `{e.args[0]}` not found.") from None

    def _connectivity_query(self, any_query=None, pre_query=None, post_query=None):
        # Filter network connection types for any type that satisfies both
        # the presynaptic and postsynaptic query. Empty queries satisfy all
        # types. The presynaptic query is satisfied if the conn type contains
        # any of the queried cell types presynaptically, and same for post.
        # The any query is satisfied if a cell type is found either pre or post.

        if post_query is None:
            post_query = set()
        if pre_query is None:
            pre_query = set()
        if any_query is None:
            any_query = set()

        def partial_query(types, query):
            return not query or any(cell_type in query for cell_type in types)

        def query(conn_type):
            pre_match = partial_query(conn_type.presynaptic.cell_types, pre_query)
            post_match = partial_query(conn_type.postsynaptic.cell_types, post_query)
            any_match = partial_query(
                conn_type.presynaptic.cell_types, any_query
            ) or partial_query(conn_type.postsynaptic.cell_types, any_query)
            return any_match and pre_match and post_match

        types = self.connectivity.values()
        return [*filter(query, types)]

    def _redo_chain(self, p_strats, c_strats, skip, force):
        p_contrib = set(p_strats)
        while True:
            # Get all the placement strategies that effect the current set of CT.
            cell_types_affected = set(
                itertools.chain(*(ps.cell_types for ps in p_contrib))
            )
            contrib = set(self.get_placement(cell_types_affected))
            if contrib:
                contrib |= set(
                    ps
                    for ps in self.get_placement()
                    if np.any(np.isin(ps.depends_on, list(contrib)))
                )
            # Keep repeating until no new contributors are fished up.
            if contrib.issubset(p_contrib):
                break
            # Grow the placement chain
            p_contrib.update(contrib)
        report(
            "Redo-affected placement: " + " ".join(ps.name for ps in p_contrib), level=2
        )

        c_contrib = set(c_strats) | set(
            []
            if len(cell_types_affected) == 0
            else self.get_connectivity(anywhere=cell_types_affected)
        )
        while True:
            contrib = c_contrib | set(
                cs
                for cs in self.get_connectivity()
                if np.any(np.isin(cs.depends_on, list(c_contrib)))
            )
            if contrib.issubset(c_contrib):
                break
            c_contrib.update(contrib)
        report(
            "Redo-affected connectivity: " + " ".join(cs.name for cs in c_contrib),
            level=2,
        )
        # Don't do greedy things without `force`
        # Error if we need to redo things the user asked to skip
        if not force and skip is not None:
            unskipped = [p.name for p in p_contrib if p.name in skip]
            if unskipped:
                chainstr = ", ".join(f"'{s.name}'" for s in (p_strats + c_strats))
                skipstr = ", ".join(f"'{s}'" for s in unskipped)
                raise RedoError(
                    f"Can't skip {skipstr}. Redoing {chainstr} requires to redo them."
                    + f" Omit {skipstr} from `skip` or use `force` (not recommended)."
                )

        for ct in cell_types_affected:
            report(f"Clearing all data of {ct.name}", level=2)
            ct.clear()

        c_sets = set(itertools.chain(*(cs.get_output_names() for cs in c_contrib)))
        for cs in c_sets:
            report(f"Clearing connectivity data of {cs}", level=2)
            try:
                cs = self.get_connectivity_set(cs)
            except DatasetNotFoundError:
                continue
            cs.clear()

        return p_contrib, c_contrib

    def get_dependency_pipelines(self):
        return [*self.configuration.morphologies]

    def get_config_diagram(self):
        from .config import make_configuration_diagram

        return make_configuration_diagram(self.configuration)

    def get_storage_diagram(self):
        dot = f'digraph "{self.configuration.name or "network"}" {{'
        for ps in self.get_placement_sets():
            dot += f'\n  {ps.tag}[label="{ps.tag} ({len(ps)} {ps.cell_type.name})"]'
        for conn in self.get_connectivity_sets():
            dot += f"\n  {conn.pre_type.name} -> {conn.post_type.name}"
            dot += f'[label="{conn.tag} ({len(conn)})"];'

        dot += "\n}\n"
        return dot

    def _load_cs_types(self, cs: ConnectivitySet, pre=None, post=None) -> ConnectivitySet:
        if pre and pre.name != cs.pre_type_name:
            raise ValueError(
                "Given and stored type mismatch:" + f" {pre.name} vs {cs.pre_type_name}"
            )
        if post and post.name != cs.post_type_name:
            raise ValueError(
                "Given and stored type mismatch:" + f" {post.name} vs {cs.post_type_name}"
            )
        try:
            cs.pre_type = self.cell_types[cs.pre_type_name]
            cs.post_type = self.cell_types[cs.post_type_name]
        except KeyError as e:
            raise NodeNotFoundError(
                f"Couldn't load '{cs.tag}' connections, missing cell type '{e.args[0]}'."
            ) from None
        return cs

    def create_job_pool(self, fail_fast=None, quiet=False):
        id_pool = self._comm.bcast(int(time.time()), root=0)
        pool = JobPool(
            id_pool,
            self,
            fail_fast=fail_fast,
            workflow=getattr(self, "_workflow", None),
        )
        try:
            # Check whether stdout is a TTY, and that it is larger than 0x0
            # (e.g. MPI sets it to 0x0 unless an xterm is emulated).
            tty = os.isatty(sys.stdout.fileno()) and sum(os.get_terminal_size())
        except Exception:
            tty = False
        if tty:
            fps = 25
            default_listener = TTYTerminalListener(fps)
            default_max_wait = 1 / fps
        else:
            default_listener = NonTTYTerminalListener()
            default_max_wait = None
        if self._pool_listeners:
            for listener, max_wait in self._pool_listeners:
                pool.add_listener(listener, max_wait=max_wait)
        elif not quiet:
            pool.add_listener(default_listener, max_wait=default_max_wait)
        return pool

    def register_listener(self, listener, max_wait=None):
        self._pool_listeners.append((listener, max_wait))

    def remove_listener(self, listener):
        for i, (l_, _) in enumerate(self._pool_listeners):
            if l_ is listener:
                self._pool_listeners.pop(i)
                break

    def register_pool_cached_item(self, id, cleanup):
        """
        Registers a cleanup function for items cached during a parallel workflow. Internal
        use only.

        :param id: Id of the cached item. Should be unique but identical across MPI nodes
        :param cleanup: A callable that cleans up the cached item.
        """
        if id in self._pool_cache:
            raise RuntimeError(f"Pool cache item '{id}' already exists.")
        self._pool_cache[id] = cleanup


class ReportListener:
    def __init__(self, scaffold, file):
        self.file = file
        self.scaffold = scaffold

    def __call__(self, progress):
        report(
            str(progress.progression)
            + "+"
            + str(progress.duration)
            + "+"
            + str(progress.time),
            token="simulation_progress",
        )


__all__ = ["ReportListener", "Scaffold", "from_storage"]
