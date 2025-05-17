"""
Glia Test Mods

Test collection of NMODL assets.

Glia asset bundle. If the Glia Asset Manager (`nmodl-glia`) is installed, the NMODL assets
in this package will automatically be available in your Glia library for use in the Arbor
and NEURON brain simulation engines.
"""

from pathlib import Path

from glia import Mod, Package

__version__ = "1.0.0"
package = Package(
    "glia_test_mods",
    Path(__file__).resolve().parent,
    mods=[
        Mod("mods/Na__0.mod", "Na", dialect="neuron"),
        Mod("mods/AMPA__0.mod", "AMPA", is_point_process=True, dialect="neuron"),
        Mod(
            "mods/AMPA__1.mod",
            "AMPA",
            variant="1",
            is_point_process=True,
            dialect="neuron",
        ),
        Mod("mods/Na__t.mod", "Na", variant="t", dialect="neuron"),
        Mod("mods/arbor/Cav2_1.mod", "Cav2_1", dialect="arbor"),
    ],
)
