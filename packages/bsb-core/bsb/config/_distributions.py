import typing

import errr
import numpy as np
import scipy.stats.distributions as _distributions

from .. import config
from ..exceptions import DistributionCastError
from . import types

if typing.TYPE_CHECKING:  # pragma: nocover
    from ..core import Scaffold

# Scan the scipy distributions module for all distribution names. Ignore `_gen` which are
# the factory functions for the distribution classes. `rvs` is a duck type check.
_available_distributions = [
    d
    for d, v in _distributions.__dict__.items()
    if hasattr(v, "rvs") and not d.endswith("_gen")
]
_available_distributions.append("constant")


@config.node
class Distribution:
    scaffold: "Scaffold"
    distribution: str = config.attr(
        type=types.in_(_available_distributions), required=True
    )
    """
    Name of the scipy.stats distribution function.
    """
    parameters: dict[str, typing.Any] = config.catch_all(type=types.any_())
    """
    Parameters to pass to the distribution.
    """

    def __init__(self, **kwargs):
        if self.distribution == "constant":
            self._distr = _ConstantDistribution(self.parameters["constant"])
            return

        try:
            self._distr = getattr(_distributions, self.distribution)(**self.parameters)
        except Exception as e:
            errr.wrap(
                DistributionCastError,
                e,
                prepend=f"Can't cast to '{self.distribution}': ",
            )

    def draw(self, n, rng: "np.random.Generator | None" = None):
        """
        Draw n random samples from the distribution.

        Drawn through the distribution's own inverse CDF
        (:meth:`~scipy.stats.rv_continuous.ppf`) rather than
        :meth:`~scipy.stats.rv_continuous.rvs`, on uniform draws taken from `rng`
        itself rather than handed to scipy as a ``random_state``. `rvs` would have
        put scipy in charge of validating `rng`, and scipy accepts only a real
        :class:`numpy.random.Generator` or :class:`~numpy.random.RandomState`,
        checked by ``isinstance`` rather than by which methods it has -- which a
        generator kind with nothing of numpy's behind it (one backed by
        ``bsb_native``'s Rust, say) is not, and cannot be made to satisfy short of
        wrapping a real numpy bit generator around it just to pass the check.
        Drawing the uniforms ourselves needs only ``rng.random(n)``, which is what
        every generator kind already has to answer -- unlike the rest of the
        framework, which also reaches for ``.integers()`` and ``.choice()``, so
        `rng` is typed here more strictly than it is actually required to be.

        This is not free: inverse-CDF sampling is scipy's generic fallback, not the
        specialised, faster and more precise sampler some distributions ship their
        own version of (the normal distribution among them), so a draw here costs
        more and, in the extreme tails, resolves less precisely than `rvs` would
        have given the same generator. A discrete distribution's draw is also
        `ppf`'s own return type, `float64`, not the `int` `rvs` gives -- cast it
        where an integer is needed, as the built-in call sites already do.

        :param n: Number of samples to draw.
        :param rng: Generator to draw from, keyed the way a caller drawing as part
            of a reconstruction already has one, e.g. from
            :meth:`RngConsumer.get_rng <bsb.rng.RngConsumer.get_rng>`. Left unset,
            falls back to an unseeded draw.
        """
        quantiles = rng.random(n) if rng is not None else np.random.random(n)
        return self._distr.ppf(quantiles)

    def definition_interval(self, epsilon=0):
        """
        Returns the `epsilon` and 1 - `epsilon` values of
        the distribution Percent point function.

        :param float epsilon: ratio of the interval to ignore
        """
        if epsilon < 0 or epsilon > 1:
            raise ValueError("Epsilon must be between 0 and 1")
        return self._distr.ppf(epsilon), self._distr.ppf(1 - epsilon)

    def cdf(self, value):
        """
        Returns the result of the cumulative distribution function for `value`

        :param float value: value to evaluate
        """
        return self._distr.cdf(value)

    def sf(self, value):
        """
        Returns the result of the Survival function for `value`

        :param float value: value to evaluate
        """
        return self._distr.sf(value)

    def __getattr__(self, attr):
        if "_distr" not in self.__dict__:
            raise AttributeError("No underlying _distr found for distribution node.")
        return getattr(self._distr, attr)


class _ConstantDistribution:
    def __init__(self, const):
        self.const = const

    def rvs(self, size):
        return np.full(size, self.const, dtype=type(self.const))

    def ppf(self, q):
        # A constant's inverse CDF is itself at every quantile, so `draw` -- and
        # `definition_interval`, which was already calling this unconditionally --
        # both work for a `constant` distribution without special-casing it.
        return np.full(np.shape(q), self.const, dtype=type(self.const))
