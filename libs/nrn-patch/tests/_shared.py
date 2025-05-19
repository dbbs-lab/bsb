import contextlib
import gc
import unittest

with contextlib.suppress(ImportError):
    # Import mpi4py before patch is imported during the tests.
    # noinspection PyPackageRequirements
    import mpi4py.MPI  # noqa: F401


class NeuronTestCase(unittest.TestCase):
    def tearDown(self):
        gc.collect()
