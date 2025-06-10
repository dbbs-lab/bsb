import abc

import arbor
from bsb import CellModel, ConfigurationError, PlacementSet, config, types

from .adapter import SingleReceiverCollection


@config.dynamic(
    attr_name="model_strategy",
    auto_classmap=True,
    required=True,
    classmap_entry=None,
)
class ArborCell(CellModel):
    model_strategy: config.ConfigurationAttribute
    """
    Optional importable reference to a different modelling strategy than the default
    Arborize strategy.
    """
    gap = config.attr(type=bool, default=False)
    """Is this synapse a gap junction?"""
    model = config.attr(type=types.class_(), required=True)
    """Importable reference to the arborize model describing the cell type."""

    @abc.abstractmethod
    def cache_population_data(self, simdata, ps: PlacementSet):
        pass

    @abc.abstractmethod
    def discard_population_data(self):
        pass

    @abc.abstractmethod
    def get_prefixed_catalogue(self):
        pass

    @abc.abstractmethod
    def get_cell_kind(self, gid):
        pass

    @abc.abstractmethod
    def make_receiver_collection(self):
        pass

    def get_description(self, gid):
        morphology, labels, decor = self.model.cable_cell_template()
        labels = self._add_labels(gid, labels, morphology)
        decor = self._add_decor(gid, decor)
        cc = arbor.cable_cell(morphology, labels, decor)
        return cc


@config.node
class LIFCell(ArborCell, classmap_entry="lif"):
    model = config.unset()
    """Importable reference to the arborize model describing the cell type."""
    constants = config.dict(type=types.any_())
    """Dictionary linking the parameters' name to its value."""

    def cache_population_data(self, simdata, ps: PlacementSet):
        pass

    def discard_population_data(self):
        pass

    def get_prefixed_catalogue(self):
        return None, None

    def get_cell_kind(self, gid):
        return arbor.cell_kind.lif

    def get_description(self, gid):
        cell = arbor.lif_cell("-1_-1", "-1_-1_0")
        try:
            for k, v in self.constants.items():
                setattr(cell, k, v * getattr(cell, k).units)
        except AttributeError:
            node_name = type(self).constants.get_node_name(self)
            raise ConfigurationError(
                f"'{k}' is not a valid LIF parameter in '{node_name}'."
            ) from None
        return cell

    def make_receiver_collection(self):
        return SingleReceiverCollection()
