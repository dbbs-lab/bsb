from pathlib import Path

from glia import Mod, Package

package = Package(
    "patch_extensions",
    Path(__file__).resolve().parent,
    mods=[Mod("mod/VecStim.mod", "VecStim", variant="0", is_artificial_cell=True)],
)
