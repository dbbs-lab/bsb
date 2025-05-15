import builtins
import typing

import errr
import nest.random.hl_api_random as _distributions
from bsb import DistributionCastError, Scaffold, TypeHandler, config, types

_available_distributions = [d for d in _distributions.__all__]


@config.node
class NestRandomDistribution:
    """
    Class to handle NEST random distributions.
    """

    scaffold: "Scaffold"
    distribution: str = config.attr(
        type=types.in_(_available_distributions), required=True
    )
    """Distribution name. Should correspond to a function of nest.random.hl_api_random"""
    parameters: dict[str, typing.Any] = config.catch_all(type=types.any_())
    """Dictionary of parameters to assign to the distribution. 
    Should correspond to NEST's"""

    def __init__(self, **kwargs):
        try:
            self._distr = getattr(_distributions, self.distribution)(**self.parameters)
        except Exception as e:
            errr.wrap(
                DistributionCastError, e, prepend=f"Can't cast to '{self.distribution}': "
            )

    def __call__(self):
        return self._distr

    def __getattr__(self, attr):
        # hasattr does not work here. So we use __dict__
        if "_distr" not in self.__dict__:
            raise AttributeError("No underlying _distr found for distribution node.")
        return getattr(self._distr, attr)


class nest_parameter(TypeHandler):
    """
    Type validator. Type casts the value or node to a Nest parameter, that can be either
    a value or a NestRandomDistribution.
    """

    def __call__(self, value, _key=None, _parent=None):
        if isinstance(value, builtins.dict) and "distribution" in value:
            return NestRandomDistribution(**value, _key=_key, _parent=_parent)
        return value

    @property
    def __name__(self):  # pragma: nocover
        return "nest parameter"

    def __inv__(self, value):
        return value
