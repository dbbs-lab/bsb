########
Scaffold
########

:class:`Scaffold <bsb:bsb.core.Scaffold>` is the main object of the BSB infrastructure (see the
:doc:`/getting-started/top-level-guide` for an introduction to this class).

Properties
----------

The Scaffold object tights together the network description
of the ``Configuration`` with the data stored in the :class:`Storage <bsb:bsb.storage.Storage>`.
You can access the latter classes with respectively the
:attr:`scaffold.configuration <bsb:bsb.core.Scaffold.configuration>` and the
:attr:`scaffold.storage <bsb:bsb.core.Scaffold.storage>` attributes.
Scaffold also provides a direct access to all of its main configuration components as class attributes:

- :attr:`scaffold.network <bsb:bsb.core.Scaffold.network>` -> :class:`NetworkNode<bsb:bsb.config._config.NetworkNode>`
- :attr:`scaffold.regions <bsb:bsb.core.Scaffold.regions>` -> :class:`Region<bsb:bsb.topology.region.Region>`
- :attr:`scaffold.partitions <bsb:bsb.core.Scaffold.partitions>` -> :class:`Partition <bsb:bsb.topology.partition.Partition>`
- :attr:`scaffold.cell_types <bsb:bsb.core.Scaffold.cell_types>` -> :class:`CellType <bsb:bsb.cell_types.CellType>`
- :attr:`scaffold.morphologies <bsb:bsb.core.Scaffold.morphologies>` -> :class:`Morphology <bsb:bsb.morphologies.Morphology>`
- :attr:`scaffold.placement <bsb:bsb.core.Scaffold.placement>` -> :class:`PlacementStrategy <bsb:bsb.placement.strategy.PlacementStrategy>`
- :attr:`scaffold.connectivity <bsb:bsb.core.Scaffold.connectivity>` -> :class:`ConnectionStrategy <bsb:bsb.connectivity.strategy.ConnectionStrategy>`
- :attr:`scaffold.simulations <bsb:bsb.core.Scaffold.simulations>` -> :class:`Simulation <bsb:bsb.simulation.simulation.Simulation>`
- :attr:`scaffold.after_placement <bsb:bsb.core.Scaffold.after_placement>` -> :class:`AfterPlacementHook <bsb:bsb.postprocessing.AfterPlacementHook>`
- :attr:`scaffold.after_connectivity <bsb:bsb.core.Scaffold.after_connectivity>` -> :class:`AfterConnectivityHook <bsb:bsb.postprocessing.AfterConnectivityHook>`

All files stored, including the ones declared under the :guilabel:`files` component of the Configuration can
be accessed through:

- :attr:`scaffold.files <bsb:bsb.core.Scaffold.files>` -> :class:`FileStore <bsb:bsb.storage.interfaces.FileStore>`

There are also a list of methods starting with ``get_`` that allows you to retrieve these components with some
additional filtering parameters (:meth:`get_cell_types <bsb:bsb.core.Scaffold.get_cell_types>`,
:meth:`get_placement <bsb:bsb.core.Scaffold.get_placement>`,
:meth:`get_placement_of <bsb:bsb.core.Scaffold.get_placement_of>`,
:meth:`get_connectivity <bsb:bsb.core.Scaffold.get_connectivity>`)

Workflow methods
----------------

Scaffold contains also all the functions required to run the reconstruction pipeline, and to simulate
the resulting networks.
You can run the full reconstruction with the :meth:`compile <bsb:bsb.core.Scaffold.compile>` method or any of its sub-step:

- Topology creation / update: :meth:`resize <bsb:bsb.core.Scaffold.resize>`
- Cell placement: :meth:`run_placement <bsb:bsb.core.Scaffold.run_placement>`
- After placement hook: :meth:`run_after_placement <bsb:bsb.core.Scaffold.run_after_placement>`
- Cell connectivity: :meth:`run_connectivity <bsb:bsb.core.Scaffold.run_connectivity>`
- After placement hook: :meth:`run_after_connectivity <bsb:bsb.core.Scaffold.run_after_connectivity>`
- Run a simulation: :meth:`run_simulation <bsb:bsb.core.Scaffold.run_simulation>`

Similarly, you can clear the results of the reconstruction stored so far with the :meth:`clear <bsb:bsb.core.Scaffold.clear>`
or any of its sub-step:

- Cell placement: :meth:`clear_placement <bsb:bsb.core.Scaffold.clear_placement>`
- Cell connectivity: :meth:`clear_connectivity <bsb:bsb.core.Scaffold.clear_connectivity>`

Get Stored data
---------------

You can also inspect the data produced during the reconstruction from the storage:

- :class:`PlacementSet <bsb:bsb.storage.interfaces.PlacementSet>` from :meth:`get_placement_set <bsb:bsb.core.Scaffold.get_placement_set>`,
  :meth:`get_placement_sets <bsb:bsb.core.Scaffold.get_placement_sets>`
- :class:`ConnectivitySet <bsb:bsb.storage.interfaces.ConnectivitySet>` from :meth:`get_connectivity_set <bsb:bsb.core.Scaffold.get_connectivity_set>`,
  :meth:`get_connectivity_sets <bsb:bsb.core.Scaffold.get_connectivity_sets>`
