import contextlib
import unittest
from unittest import mock

import numpy as np
import requests
from bsb_test import (
    FixedPosConfigFixture,
    NumpyTestCase,
    RandomStorageFixture,
    skipIfOffline,
)
from scipy.spatial.transform import Rotation

from bsb import FileDependency, NeuroMorphoScheme, Scaffold, UrlScheme
from bsb._util import assert_samelen, rotation_matrix_from_vectors


class TestNetworkUtil(
    FixedPosConfigFixture,
    RandomStorageFixture,
    NumpyTestCase,
    unittest.TestCase,
    engine_name="hdf5",
):
    def setUp(self):
        super().setUp()
        self.network = Scaffold(self.cfg, self.storage)
        self.network.connectivity.add(
            "all_to_all",
            dict(
                strategy="bsb.connectivity.AllToAll",
                presynaptic=dict(cell_types=["test_cell"], morphology_labels=["axon"]),
                postsynaptic=dict(
                    cell_types=["test_cell"], morphology_labels=["dendrites"]
                ),
            ),
        )
        self.network.compile()

    def test_str(self):
        for obj in (
            self.network,
            *self.network.placement.values(),
            *self.network.connectivity.values(),
            self.network.get_placement_set("test_cell"),
            self.network.get_connectivity_set("all_to_all"),
        ):
            self.assertNotEqual(object.__repr__(obj), str(obj))
            self.assertNotEqual(object.__repr__(obj), repr(obj))


class TestRotationUtils(unittest.TestCase):
    def test_rotation_matrix_from_vectors(self):
        vec1 = [0, 0, 1]
        vec2 = [0, 1, 0]
        err1 = [0, 0, 0]
        err2 = [np.nan, 0, 1]
        self.assertTrue(np.all(np.eye(3) == rotation_matrix_from_vectors(vec1, vec1)))
        self.assertTrue(
            np.all(
                Rotation.from_matrix(rotation_matrix_from_vectors(vec1, vec2)).as_euler(
                    "xyz", degrees=True
                )
                == np.array([-90.0, 0.0, 0.0])
            )
        )
        with self.assertRaises(ValueError, msg="This should raise a ValueError") as _:
            rotation_matrix_from_vectors(err1, vec2)
        with self.assertRaises(ValueError, msg="This should raise a ValueError") as _:
            rotation_matrix_from_vectors(vec1, err2)


class TestUriSchemes(RandomStorageFixture, unittest.TestCase, engine_name="fs"):
    @skipIfOffline(scheme=NeuroMorphoScheme())
    def test_nm_scheme(self):
        file = FileDependency(
            "nm://AX2_scaled",
            Scaffold(storage=self.storage).files,
        )
        self.assertIs(NeuroMorphoScheme, type(file._scheme), "Expected NM scheme")
        meta = file.get_meta()
        self.assertIn("neuromorpho_data", meta)
        self.assertEqual(130892, meta["neuromorpho_data"]["neuron_id"])

    def test_nm_scheme_down(self):
        url = NeuroMorphoScheme._nm_url
        # Consistently trigger a 404 response in the NM scheme
        NeuroMorphoScheme._nm_url = "https://google.com/404"
        try:
            file = FileDependency(
                "nm://AX2_scaled",
                Scaffold(storage=self.storage).files,
            )
            with self.assertWarns(UserWarning) as _w:
                file.get_meta()
        finally:
            NeuroMorphoScheme._nm_url = url


class TestOfflineUrlScheme(RandomStorageFixture, unittest.TestCase, engine_name="fs"):
    """
    Cached URL files must stay usable when the host can't be reached, e.g. on compute
    nodes whose outbound connection is closed once the job starts.
    """

    url = "https://example.com/cached.txt"

    def setUp(self):
        super().setUp()
        self.file = FileDependency(self.url, Scaffold(storage=self.storage).files)
        with mock.patch.object(
            UrlScheme, "get_meta", return_value={"headers": {"ETag": "v1"}}
        ):
            self.file.store_content(b"cached content")

    @contextlib.contextmanager
    def _head_raises(self, error):
        with mock.patch.object(requests.Session, "head", side_effect=error):
            yield

    def test_connection_error_keeps_cache(self):
        with self._head_raises(requests.ConnectionError("Network is unreachable")):
            with self.assertWarns(UserWarning):
                self.assertFalse(self.file.should_update(), "should keep cached copy")
            self.assertEqual(b"cached content", self.file.get_content()[0], "not cached")

    def test_timeout_keeps_cache(self):
        with (
            self._head_raises(requests.ConnectTimeout("timed out")),
            self.assertWarns(UserWarning),
        ):
            self.assertFalse(self.file.should_update(), "should keep cached copy")

    def test_other_request_errors_propagate(self):
        with (
            self._head_raises(requests.TooManyRedirects("redirect loop")),
            self.assertRaises(requests.TooManyRedirects),
        ):
            self.file.should_update()

    def test_http_status_is_not_a_connection_error(self):
        # HTTP statuses don't raise: a 404 comes back as a response without validation
        # headers, and falls through to the expiration check, unlike an unreachable host.
        not_found = mock.Mock(status_code=404, headers={"Content-Length": "0"})
        with mock.patch.object(requests.Session, "head", return_value=not_found):
            self.assertFalse(self.file.should_update(), "cached copy hasn't expired yet")
        changed = mock.Mock(status_code=200, headers={"ETag": "v2"})
        with mock.patch.object(requests.Session, "head", return_value=changed):
            self.assertTrue(self.file.should_update(), "new ETag should trigger update")


class TestAssertSameLength(unittest.TestCase):
    def test_same_length(self):
        assert_samelen([1, 2, 3], [4, 5, 6])
        with self.assertRaises(AssertionError):
            assert_samelen([1, 2], [2])
        assert_samelen([[1, 2]], [3])
        assert_samelen([], [])
