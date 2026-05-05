"""
NEST simulation adapter for the BSB framework.
"""

# fmt: off
# isort: off
from bsb._trace import t as _t  # noqa: E402

_t("bsb_nest/__init__.py: enter")
_t("bsb_nest/__init__.py: pre  from bsb import SimulationBackendPlugin")
from bsb import SimulationBackendPlugin  # noqa: E402
_t("bsb_nest/__init__.py: post from bsb import SimulationBackendPlugin")

_t("bsb_nest/__init__.py: pre  from .adapter import NestAdapter  *** triggers `import nest` ***")
from .adapter import NestAdapter  # noqa: E402
_t("bsb_nest/__init__.py: post from .adapter import NestAdapter")
_t("bsb_nest/__init__.py: pre  from .devices import ...")
from .devices import (  # noqa: E402
    DCGenerator,
    Multimeter,
    PoissonGenerator,
    SinusoidalPoissonGenerator,
    SpikeRecorder,
)
_t("bsb_nest/__init__.py: post from .devices import ...")
_t("bsb_nest/__init__.py: pre  from .simulation import NestSimulation")
from .simulation import NestSimulation  # noqa: E402
_t("bsb_nest/__init__.py: post from .simulation import NestSimulation")
# fmt: on
# isort: on

__plugin__ = SimulationBackendPlugin(Simulation=NestSimulation, Adapter=NestAdapter)

__all__ = [
    "DCGenerator",
    "Multimeter",
    "NestAdapter",
    "NestSimulation",
    "PoissonGenerator",
    "SinusoidalPoissonGenerator",
    "SpikeRecorder",
]
