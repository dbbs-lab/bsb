import typing

import errr
from bsb import (
    DistributionCastError,
    Parameter,
    Scaffold,
    config,
    constant,
    parameter,
    types,
)


class _LazyDistributionNames:
    """Defers ``import nest`` until the validator actually needs to check a name."""

    def __contains__(self, item):
        import nest.random.hl_api_random as _distributions

        return item in _distributions.__all__


@config.node
class NestRandomDistribution(Parameter):
    """
    A NEST random distribution, drawn per node by NEST itself.

    It yields the one :class:`nest.Parameter` object NEST expands across the nodes it
    is assigned to, so it reports itself as constant: nothing on our side broadcasts
    it.
    """

    is_constant = True

    scaffold: "Scaffold"
    distribution: str = config.attr(
        type=types.in_(_LazyDistributionNames()), required=True
    )
    """Distribution name. Should correspond to a function of nest.random.hl_api_random"""
    parameters: dict[str, typing.Any] = config.catch_all(type=types.any_())
    """Dictionary of parameters to assign to the distribution.
    Should correspond to NEST's"""

    def __init__(self, **kwargs):
        import nest.random.hl_api_random as _distributions

        try:
            self._distr = getattr(_distributions, self.distribution)(**self.parameters)
        except Exception as e:
            errr.wrap(
                DistributionCastError, e, prepend=f"Can't cast to '{self.distribution}': "
            )

    def __call__(self):
        return self._distr

    def compute(self, *args, **kwargs):
        return self._distr

    def __getattr__(self, attr):
        # hasattr does not work here. So we use __dict__
        if "_distr" not in self.__dict__:
            raise AttributeError("No underlying _distr found for distribution node.")
        return getattr(self._distr, attr)


class nest_parameter(parameter):
    """
    Cast a value to a parameter, adding NEST's own random distributions.

    Extends the framework handler with one more shorthand, so every notation NEST
    users already write keeps working:

    * ``{"distribution": "uniform", ...}`` becomes a :class:`.NestRandomDistribution`;
    * everything else is handled by :class:`~bsb.simulation.parameter.parameter`.
    """

    def __call__(self, value, _key=None, _parent=None):
        if isinstance(value, dict) and "distribution" in value:
            return NestRandomDistribution(**value, _key=_key, _parent=_parent)
        return super().__call__(value, _key=_key, _parent=_parent)

    @property
    def __name__(self):  # pragma: nocover
        return "nest parameter"

    def __inv__(self, value):
        if isinstance(value, NestRandomDistribution):
            return value.__tree__()
        return super().__inv__(value)


class nest_constant(constant):
    """
    Cast a value to a constant, adding NEST's own random distributions.

    The narrow counterpart of :class:`.nest_parameter`, for ``constants`` blocks. A
    distribution counts as a constant here because NEST expands it itself: nothing
    on our side computes per cell or per connection.
    """

    def __call__(self, value, _key=None, _parent=None):
        if isinstance(value, dict) and "distribution" in value:
            return NestRandomDistribution(**value, _key=_key, _parent=_parent)
        return super().__call__(value, _key=_key, _parent=_parent)

    @property
    def __name__(self):  # pragma: nocover
        return "nest constant"

    def __inv__(self, value):
        if isinstance(value, NestRandomDistribution):
            return value.__tree__()
        return super().__inv__(value)
