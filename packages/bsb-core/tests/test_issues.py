import os
import unittest
from types import NoneType

from bsb_test import RandomStorageFixture, timeout

from bsb import (
    BootError,
    CellType,
    CfgReferenceError,
    Chunk,
    Configuration,
    FixedPositions,
    PlacementIndications,
    Reference,
    Scaffold,
    config,
)


def relative_to_tests_folder(path):
    return os.path.join(os.path.dirname(__file__), path)


class BothReference(Reference):
    def __call__(self, root, here):
        merged = root.examples.copy()
        merged.update(root.extensions)
        return merged

    @property
    def type(self):
        return NoneType


@config.node
class Example:
    mut_ex = config.attr(required=True)


@config.node
class Extension:
    ex_mut = config.attr(type=int, required=True)
    ref = config.ref(BothReference(), required=True)


@config.root
class Root430:
    examples = config.dict(type=Example, required=True)
    extensions = config.dict(type=Extension, required=True)


class TestIssues(RandomStorageFixture, unittest.TestCase, engine_name="hdf5"):
    def test_430(self):
        with self.assertRaises(CfgReferenceError, msg="Regression of issue #430"):
            _config = Root430(
                examples=dict(), extensions=dict(x=dict(ex_mut=4, ref="missing"))
            )

    def test_802(self):
        """
        Test fixed positions with 0 positions.
        """
        with self.assertWarns(UserWarning):
            # Cobble some components together to test `positions=[]`
            FixedPositions(positions=[], cell_types=[], partitions=[]).place(
                Chunk((0, 0, 0), (100, 100, 100)),
                {CellType(spatial=dict(radius=1, count=1)): PlacementIndications()},
            )

    @timeout(3)
    def test_211(self):
        """
        Test if the absence of a file does not make the reconstruction
        get stuck in parallel.
        """
        cfg = Configuration.default(
            files=dict(annotations={"file": "path/to/missing/file.nrrd", "type": "nrrd"}),
        )
        with self.assertRaises(BootError):
            Scaffold(cfg, self.storage)
