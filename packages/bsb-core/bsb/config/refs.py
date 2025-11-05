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


class VoxelDatasetReference(Reference):
    def __call__(self, root, here):
        result = root.files.copy()
        to_remove = []
        for k in iter(result):
            if not isinstance(result[k], self.type):
                to_remove.append(k)
        for k in to_remove:
            del result[k]
        return result

    @property
    def type(self):
        from ..storage._files import NrrdDependencyNode

        return NrrdDependencyNode


class CellTypeReference(Reference):
    def __call__(self, root, here):
        return root.cell_types

    @property
    def type(self):
        from ..cell_types import CellType

        return CellType


class PartitionReference(Reference):
    def __call__(self, root, here):
        return root.partitions

    @property
    def type(self):
        from ..topology import Partition

        return Partition


class RegionReference(Reference):
    def __call__(self, root, here):
        return root.regions

    @property
    def type(self):
        from ..topology import Region

        return Region


class RegionalReference(Reference):
    def __call__(self, root, here):
        merged = root.regions.copy()
        merged.update(root.partitions)
        return merged

    @property
    def type(self):
        from ..topology import Partition, Region
        from .types import or_

        return or_(Partition, Region)


class PlacementReference(Reference):
    def __call__(self, root, here):
        return root.placement

    @property
    def type(self):
        from ..placement import PlacementStrategy

        return PlacementStrategy


class ConnectivityReference(Reference):
    def __call__(self, root, here):
        return root.connectivity

    @property
    def type(self):
        from ..connectivity import ConnectionStrategy

        return ConnectionStrategy


class SimCellModelReference(Reference):
    def __call__(self, root, here):
        from ..simulation.simulation import Simulation

        sim = self.up(here, Simulation)
        return sim.cell_models

    @property
    def type(self):
        from ..simulation.cell import CellModel

        return CellModel


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
