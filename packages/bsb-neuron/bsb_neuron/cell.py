import itertools

from arborize import ModelDefinition, define_model
from bsb import CellModel, config, types


@config.dynamic(
    attr_name="model_strategy", required=False, default="arborize", auto_classmap=True
)
class NeuronCell(CellModel):
    """
    Class interfacing a NEURON cell model.
    """

    model_strategy: str
    """The strategy for neuron cell creation (e.g., 'arborize')."""

    def create_instances(self, count, ids, pos, morpho, rot, additional):
        """
        Create multiple neuron cell instances.

        :param int count: Number of neuron instances to create.
        :param ids: Iterable of identifiers for each neuron instance.
        :param pos: Iterable of positions for each neuron instance.
        :param morpho: Iterable of morphology objects.
        :type morpho: bsb.morphologies.MorphologySet
        :param rot: Iterable of rotation data for each neuron instance.
        :type rot: bsb.morphologies.RotationSet
        :param additional: Dict of additional parameters with iterable values.

        :return: List of created neuron instances.
        :rtype: list
        """

        def dictzip():
            yield from (
                dict(zip(additional.keys(), values[:-1], strict=False))
                for values in itertools.zip_longest(
                    *additional.values(), itertools.repeat(count)
                )
            )

        ids, pos, morpho, rot = (
            iter(ids),
            iter(pos),
            iter(morpho),
            iter(rot),
        )
        additer = dictzip()
        return [
            self._create(next(ids), next(pos), next(morpho), next(rot), next(additer))
            for i in range(count)
        ]

    def _create(self, id, pos, morpho, rot, additional):
        if morpho is None:
            raise RuntimeError(
                f"Cell {id} of {self.name} has no morphology, "
                f"can't use {self.__class__.__name__} to construct it."
            )
        instance = self.create(id, pos, morpho, rot, additional)
        instance.id = id
        return instance


class ArborizeModelTypeHandler(types.object_):
    @property
    def __name__(self):
        return "arborized model definition"

    def __call__(self, value):
        if isinstance(value, dict):
            model = define_model(value)
            model._cfg_inv = value
            return model
        else:
            return super().__call__(value)

    def __inv__(self, value):
        inv_value = super().__inv__(value)

        if isinstance(inv_value, ModelDefinition):
            inv_value = inv_value.to_dict()
        return inv_value


@config.node
class ArborizedModel(NeuronCell, classmap_entry="arborize"):
    """
    Neuron cell model using Arborize for morphology-based neuron construction.
    """

    model = config.attr(type=ArborizeModelTypeHandler(), required=True)
    """Configuration attribute specifying the Arborize model type handler."""
    _schematics = {}

    def create(self, id, pos, morpho, rot, additional):
        from arborize import bsb_schematic, neuron_build

        self.model.use_defaults = True
        schematic = bsb_schematic(morpho, self.model)
        return neuron_build(schematic)


class Shim:
    pass


@config.node
class ShimModel(NeuronCell, classmap_entry="shim"):
    def create(self, id, pos, morpho, rot, additional):
        return Shim()
