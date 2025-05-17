import unittest

import glia._mpi
from glia import PackageError

skipParallel = unittest.skipIf(glia._mpi.parallel_run, "Skip during parallel tests.")


def skipUnlessInstalled(package_name: str):
    try:
        glia.package(package_name)
        installed = True
    except PackageError:
        installed = False
    return unittest.skipUnless(
        installed, f"Skipped because '{package_name}' is not installed."
    )


def skipIfInstalled(package_name: str = None):
    if package_name is None:
        return unittest.skipIf(
            glia.get_packages(), "Skipped because there are installed packages."
        )
    try:
        glia.package(package_name)
        installed = True
    except PackageError:
        installed = False
    return unittest.skipIf(installed, f"Skipped because '{package_name}' is installed.")


skipUnlessTestMods = skipUnlessInstalled("glia_test_mods")
