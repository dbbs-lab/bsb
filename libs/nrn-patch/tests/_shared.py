import gc
import unittest

try:
    # Import mpi4py before patch is imported during the tests.
    # noinspection PyPackageRequirements
    import mpi4py.MPI
except ImportError:
    pass


class NeuronTestCase(unittest.TestCase):
    def tearDown(self):
        gc.collect()
