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
    def create_instances(self, count, ids, pos, morpho, rot, additional):
        """
        type morpho: bsb.morphologies.MorphologySet
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
    model = config.attr(type=ArborizeModelTypeHandler(), required=True)
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
