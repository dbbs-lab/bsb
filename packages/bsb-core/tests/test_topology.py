import os
import unittest

import nrrd
import numpy as np
from bsb_test import NumpyTestCase, RandomStorageFixture, get_data_path

from bsb import (
    AllenApiError,
    AllenStructure,
    Configuration,
    ConfigurationError,
    LayoutError,
    NodeNotFoundError,
    Scaffold,
    topology,
)


def single_layer():
    c = topology.Layer(thickness=150)
    r = topology.Stack(children=[c])
    topology.create_topology([r], np.array([0, 0, 0]), np.array([100, 100, 100]))
    return r, c


class TestCreateTopology(unittest.TestCase):
    def test_single(self):
        r = topology.Region(name="R", children=[])
        t = topology.create_topology([r], np.array([0, 0, 0]), np.array([100, 100, 100]))
        self.assertEqual(r, t, "Topology with 1 root region should be the region itself")

    def test_unrelated(self):
        r = topology.Region(children=[])
        rb = topology.Region(children=[])
        t = topology.create_topology([r, rb], np.array([0, 0, 0]), np.array([1, 1, 1]))
        self.assertNotEqual(r, t, "Topology with multiple roots should be encapsulated")

    def test_2gen(self):
        r = topology.Region(children=[])
        r2 = topology.Region(children=[r])
        t = topology.create_topology([r2, r], np.array([0, 0, 0]), np.array([1, 1, 1]))
        self.assertEqual(r2, t, "Dependency interpreted as additional root")

    def test_3gen(self):
        r = topology.Region(children=[])
        r2 = topology.Region(children=[r])
        r3 = topology.Region(children=[r2])
        t = topology.create_topology(
            [r3, r2, r], np.array([0, 0, 0]), np.array([100, 100, 100])
        )
        self.assertEqual(r3, t, "Recursive dependency interpreted as additional root")


class TestTopology(unittest.TestCase):
    def test_stack(self):
        c = topology.Layer(name="c", thickness=150)
        c2 = topology.Layer(name="c2", thickness=150)
        r = topology.Stack(name="mystack", children=[c, c2])
        topology.create_topology([r], [0, 0, 0], [100, 100, 100])
        self.assertEqual(0, c.data.y)
        self.assertEqual(150, c2.data.height)
        self.assertEqual(100, c.data.width)
        self.assertEqual(100, c2.data.width)
        self.assertEqual(300, r.data.height)

    def test_partition_chunking(self):
        r, l_ = single_layer()
        cs = np.array([100, 100, 100])
        # Test 100x150x100 layer producing 2 100x100x100 chunks on top of each other
        self.assertEqual([[0, 0, 0], [0, 0, 1]], l_.to_chunks(cs).tolist())
        # Test translation by whole chunk
        l_.data.x += cs[0]
        self.assertEqual([[1, 0, 0], [1, 0, 1]], l_.to_chunks(cs).tolist())
        # Translate less than a chunk so that we overflow into an extra layer of x chunks
        l_.data.x += 1
        self.assertEqual(
            [[1, 0, 0], [1, 0, 1], [2, 0, 0], [2, 0, 1]], l_.to_chunks(cs).tolist()
        )


def skip_test_allen_api():
    try:
        AllenStructure._dl_structure_ontology()
    except AllenApiError:
        return True
    except Exception:
        pass
    return False


class TestStack(
    RandomStorageFixture, NumpyTestCase, unittest.TestCase, engine_name="hdf5"
):
    def setUp(self):
        super().setUp()
        self.origin_order = ["rhomboid1", "layer2", "rhomboid2", "layer1", "rhomboid3"]
        self.cfg = dict(
            regions=dict(
                a=dict(
                    type="stack",
                    children=self.origin_order,
                ),
                b=dict(type="group", children=["layer0"]),
            ),
            partitions=dict(
                # we set the origin to rhomboid1 so that every partition is shifted by
                # this value
                rhomboid1=dict(
                    type="rhomboid", dimensions=[10, 10, 10], origin=[0, 0, 10]
                ),
                rhomboid2=dict(
                    type="rhomboid", dimensions=[10, 10, 10], origin=[0, 0, 10]
                ),
                rhomboid3=dict(
                    type="rhomboid", dimensions=[10, 10, 10], origin=[0, 0, 20]
                ),
                layer0=dict(type="layer", thickness=10),
                layer1=dict(type="layer", thickness=10),
                layer2=dict(type="layer", thickness=10),
            ),
        )

    def _test_dimensions_offset(self, children, stack_size=10):
        for i, child in enumerate(children):
            self.assertEqual(child.name, self.origin_order[i])
            predicted_origin = np.array([0.0, 0.0, stack_size])
            self.assertClose(predicted_origin, child.data.ldc)
            dimensions = (
                child.dimensions
                if hasattr(child, "dimensions")
                else np.array([200, 200, child.thickness])
            )
            self.assertClose(predicted_origin + dimensions, child.data.mdc)
            stack_size = child.data.mdc[2]

    def test_default_order(self):
        network = Scaffold(Configuration.default(**self.cfg), self.storage)
        self._test_dimensions_offset(np.array(network.regions["a"].children))

    def test_anchor(self):
        self.cfg["regions"]["a"]["anchor"] = "rhomboid2"
        network = Scaffold(Configuration.default(**self.cfg), self.storage)
        self._test_dimensions_offset(
            np.array(network.regions["a"].children), stack_size=-10
        )


class TestNrrdVoxels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dataset, h = nrrd.read(get_data_path("orientations", "toy_annotations.nrrd"))
        copy_h = h.copy()
        copy_h["sizes"] = h["sizes"][:-1]
        nrrd.write(
            get_data_path("orientations", "bad_dimensions.nrrd"),
            dataset[:, :, 5],
            header=copy_h,
        )
        h["sizes"][2] -= 1
        nrrd.write(
            get_data_path("orientations", "bad_dataset.nrrd"),
            dataset[:, :, :-1],
            header=h,
        )

    @classmethod
    def tearDownClass(cls):
        os.remove(get_data_path("orientations", "bad_dimensions.nrrd"))
        os.remove(get_data_path("orientations", "bad_dataset.nrrd"))

    def test_bad_dimensions(self):
        cfg = Configuration.default(
            partitions=dict(
                a=dict(
                    type="nrrd",
                    sources={
                        "annotations": get_data_path(
                            "orientations", "bad_dimensions.nrrd"
                        ),
                    },
                )
            ),
        )
        part = cfg.partitions.a
        with self.assertRaises(
            ConfigurationError, msg="Sources with 2 dimensions should raise an exception"
        ):
            _ = part.voxel_size

        cfg = Configuration.default(
            partitions=dict(
                a=dict(
                    type="nrrd",
                    sources={
                        "annotations": get_data_path(
                            "orientations", "toy_annotations.nrrd"
                        ),
                        "second_ann": get_data_path("orientations", "bad_dataset.nrrd"),
                    },
                )
            ),
        )
        part = cfg.partitions.a
        with self.assertRaises(
            ConfigurationError,
            msg="Sources with different dimensions should raise an exception.",
        ):
            _ = part.voxel_size

        cfg = Configuration.default(
            partitions=dict(
                a=dict(
                    type="nrrd",
                    sources={
                        "annotations": get_data_path(
                            "orientations", "toy_annotations.nrrd"
                        ),
                        "second_ann": get_data_path("orientations", "bad_dataset.nrrd"),
                    },
                    strict=False,
                )
            ),
        )
        part = cfg.partitions.a
        with self.assertRaises(
            ConfigurationError,
            msg="Sources with different dimensions should raise an exception.",
        ):
            _ = part.voxel_size

    def test_mask_value(self):
        cfg = Configuration.default(
            partitions=dict(
                a=dict(
                    type="nrrd",
                    sources={
                        "annotations": get_data_path(
                            "orientations", "toy_annotations.nrrd"
                        ),
                    },
                    mask_value=10690,
                )
            ),
        )
        part = cfg.partitions.a
        vs = part.voxelset
        self.assertEqual(24, len(vs), "Region has that many voxels")


@unittest.skipIf(
    skip_test_allen_api(),
    "Allen API is down",
)
class TestAllenVoxels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dataset, h = nrrd.read(get_data_path("orientations", "toy_annotations.nrrd"))
        h["sizes"][2] -= 1
        dataset = dataset[:, :, :-1]
        nrrd.write(get_data_path("orientations", "bad_dataset.nrrd"), dataset, header=h)

    @classmethod
    def tearDownClass(cls):
        os.remove(get_data_path("orientations", "bad_dataset.nrrd"))

    def test_val(self):
        cfg = Configuration.default(
            partitions=dict(a=dict(type="allen", struct_name="VAL")),
        )
        part = cfg.partitions.a
        vs = part.voxelset
        self.assertEqual(52314, len(vs), "VAL is that many voxels")
        self.assertEqual(52314 * 25**3, part.volume(), "VAL occupies this much space")
        self.assertTrue(
            np.allclose([(5975, 3550, 3950), (7125, 5100, 7475)], vs.bounds),
            "VAL has those bounds",
        )
        not_impl = "We don't support transforming voxel partitions yet. Contribute it!"
        for t in ("translate", "scale", "rotate"):
            with self.subTest(transform=t):
                transform = getattr(part, t)
                with self.assertRaises(LayoutError, msg=not_impl):
                    transform(0)

    def test_optional_struct_key(self):
        """
        Test only if AllenStructure correctly assign default struct_name, the actual
        function is tested in test_val()
        """
        cfg = Configuration.default(
            partitions=dict(val=dict(type="allen")),
        )
        part = cfg.partitions.val
        vs = part.voxelset
        self.assertEqual(52314, len(vs), "VAL is that many voxels")

    def test_mask_nrrd(self):
        cfg = Configuration.default(
            regions=dict(br=dict(children=["a"])),
            partitions=dict(
                a=dict(
                    type="allen",
                    mask_source=get_data_path("orientations", "toy_annotations.nrrd"),
                    struct_id=10690,
                )
            ),
        )
        part = cfg.partitions.a
        vs = part.voxelset
        self.assertEqual(24, len(vs), "Region has that many voxels")
        self.assertEqual(24 * 25**3, part.volume(), "Region occupies this much space")
        mask = part.get_structure_mask(1049)  # DEC id
        self.assertEqual(
            mask.shape, (528, 320, 456), "Mask should match Allen dimensions"
        )
        self.assertEqual(
            np.count_nonzero(mask), 85475, "DEC should have this many voxels."
        )
        part.mask_source = None
        self.assertFalse(hasattr(part, "_annotations_file"))
        self.assertEqual(
            part.annotations.raw.shape, (528, 320, 456), "Should download allen dataset"
        )

    def test_wrong_sizes_nrrd(self):
        cfg = Configuration.default(
            regions=dict(br=dict(children=["a"])),
            partitions=dict(
                a=dict(
                    type="allen",
                    mask_source=get_data_path("orientations", "toy_annotations.nrrd"),
                    struct_id=10690,
                    atlas_datasets={
                        "orientations": get_data_path(
                            "orientations", "toy_orientations.nrrd"
                        ),
                        "wrong_dim": get_data_path("orientations", "bad_dataset.nrrd"),
                    },
                )
            ),
        )
        part = cfg.partitions.a
        with self.assertRaises(ConfigurationError, msg="Shape should mismatch"):
            _ = part.voxelset

    def test_wrong_ids(self):
        cfg = Configuration.default(
            regions=dict(br=dict(children=["a"])),
            partitions=dict(
                a=dict(
                    type="allen",
                    mask_source=get_data_path("orientations", "toy_annotations.nrrd"),
                    struct_id=1e7,
                )
            ),
        )
        part = cfg.partitions.a
        with self.assertRaises(NodeNotFoundError, msg="This id should be not exist"):
            _ = part.voxelset

        with self.assertRaises(
            TypeError, msg="Only string, int or float should be accepted"
        ):
            _ = AllenStructure.get_structure_idset([852])
