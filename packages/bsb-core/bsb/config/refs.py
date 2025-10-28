"""
This module contains shorthand ``reference`` definitions. References are used in the
configuration module to point to other locations in the Configuration object.

Minimally a reference is a function that takes the configuration root and the current
node as arguments, and returns another node in the configuration object::

  def some_reference(root, here):
      return root.other.place

More advanced usage of references will include custom reference errors.
"""

import abc


class Reference(abc.ABC):  # noqa: B024
    """
    Interface to create reference to pass to `bsb.config.ref`
    or `bsb.config.reflist`
    """

    def __call__(self, root, here):
        """
        Function to retrieve the location of the reference

        :param root: root of the configuration object
        :param here: current node in the configuration object
        """
        return here

    def up(self, here, to=None):
        """
        Get the parent node of the configuration node ``here``.
        If ``to`` is provided, will search ``here``'s ascendants
        until one matches ``to``'s type.

        :param here: starting node
        :param to: type of the ascendant to find
        :return: The first matching parent node of ``here``
        """
        if to is None:
            return here._config_parent
        while not isinstance(here, to):
            try:
                here = here._config_parent
            except AttributeError:
                return None
        return here

    def is_ref(self, value):
        """
        Check if the provided value corresponds to
        the type of the reference

        :param value: value to check
        :rtype: bool
        :return: True if the value has the type of the reference
        """
        return not isinstance(value, str)

    @property
    @abc.abstractmethod
    def type(self):  # pragma: nocover
        """
        Return the type of the reference
        """
        pass


class FileReference(Reference):
    def __call__(self, root, here):
        return root.files

    @property
    def type(self):
        from ..storage._files import FileDependencyNode

        return FileDependencyNode

    def is_ref(self, value):
        from ..storage._files import FileDependencyNode

        return isinstance(value, FileDependencyNode)


class VoxelDatasetReference(Reference):
    def __call__(self, root, here):
        result = root.files.copy()
        for k in iter(result):
            if not isinstance(result[k], self.type):
                del result[k]
        return result

    @property
    def type(self):
        from ..storage._files import NrrdDependencyNode

        return NrrdDependencyNode

    def is_ref(self, value):
        from ..storage._files import NrrdDependencyNode

        return isinstance(value, NrrdDependencyNode)


class CellTypeReference(Reference):
    def __call__(self, root, here):
        return root.cell_types

    @property
    def type(self):
        from ..cell_types import CellType

        return CellType

    def is_ref(self, value):
        from ..cell_types import CellType

        return isinstance(value, CellType)


class PartitionReference(Reference):
    def __call__(self, root, here):
        return root.partitions

    @property
    def type(self):
        from ..topology import Partition

        return Partition

    def is_ref(self, value):
        from ..topology import Partition

        return isinstance(value, Partition)


class RegionReference(Reference):
    def __call__(self, root, here):
        return root.regions

    @property
    def type(self):
        from ..topology import Region

        return Region

    def is_ref(self, value):
        from ..topology import Region

        return isinstance(value, Region)


class RegionalReference(Reference):
    def __call__(self, root, here):
        merged = root.regions.copy()
        merged.update(root.partitions)
        return merged

    @property
    def type(self):
        from ..topology import Partition, Region

        return Region | Partition

    def is_ref(self, value):
        from ..topology import Partition, Region

        return isinstance(value, Region | Partition)


class PlacementReference(Reference):
    def __call__(self, root, here):
        return root.placement

    @property
    def type(self):
        from ..placement import PlacementStrategy

        return PlacementStrategy

    def is_ref(self, value):
        from ..placement import PlacementStrategy

        return isinstance(value, PlacementStrategy)


class ConnectivityReference(Reference):
    def __call__(self, root, here):
        return root.connectivity

    @property
    def type(self):
        from ..connectivity import ConnectionStrategy

        return ConnectionStrategy

    def is_ref(self, value):
        from ..connectivity import ConnectionStrategy

        return isinstance(value, ConnectionStrategy)


class SimCellModelReference(Reference):
    def __call__(self, root, here):
        from ..simulation.simulation import Simulation

        sim = self.up(here, Simulation)
        return sim.cell_models

    @property
    def type(self):
        from ..simulation.cell import CellModel

        return CellModel

    def is_ref(self, value):
        from ..simulation.cell import CellModel

        return isinstance(value, CellModel)


file_ref = FileReference()
vox_dset_ref = VoxelDatasetReference()
cell_type_ref = CellTypeReference()
partition_ref = PartitionReference()
placement_ref = PlacementReference()
connectivity_ref = ConnectivityReference()
regional_ref = RegionalReference()
region_ref = RegionReference()
sim_cell_model_ref = SimCellModelReference()

__all__ = [
    "Reference",
    "file_ref",
    "vox_dset_ref",
    "cell_type_ref",
    "partition_ref",
    "placement_ref",
    "connectivity_ref",
    "regional_ref",
    "region_ref",
    "sim_cell_model_ref",
]
__api__ = ["Reference"]
