import os
import tempfile
import unittest
import warnings

import h5py
from bsb_test import skip_parallel


class TestHDF5Provenance(unittest.TestCase):
    """Verify the HDF5 engine writes & maintains the provenance bundle."""

    def _new_storage(self, path):
        from bsb.storage import Storage

        return Storage("hdf5", path)

    def test_create_writes_full_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "net.hdf5")
            s = self._new_storage(path)
            md = s._engine.metadata
            for key in (
                "storage_id",
                "state_id",
                "bsb_schema_version",
                "created_at",
                "modified_at",
                "bsb_version",
                "engine_name",
                "engine_version",
                "plugins",
                "host",
                "mpi_size",
            ):
                self.assertIn(key, md, f"missing root attr: {key}")
            self.assertEqual(md["engine_name"], "hdf5")
            self.assertEqual(md["state_id"], 0)
            self.assertEqual(md["bsb_schema_version"], 1)
            # Plugins manifest contains at least the two storage engines.
            engines = (md.get("plugins") or {}).get("storage.engines", {})
            self.assertIn("hdf5", engines)
            self.assertIn("fs", engines)

    def test_storage_id_is_stable_uuid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "net.hdf5")
            s1 = self._new_storage(path)
            id1 = s1._engine.storage_id
            # Re-open same file; id must not change.
            s2 = self._new_storage(path)
            self.assertEqual(s2._engine.storage_id, id1)

    def test_state_bumps_on_mutation(self):
        from bsb.config import Configuration
        from bsb.core import Scaffold

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "net.hdf5")
            s = self._new_storage(path)
            self.assertEqual(s._engine.state_id, 0)
            s._engine._bump_state()
            self.assertEqual(s._engine.state_id, 1)
            # Going through Scaffold runs store_active_config which writes via
            # the file store -> exercises the mutation-bump pathway.
            before = s._engine.state_id
            Scaffold(Configuration.default(), storage=s)
            self.assertGreater(s._engine.state_id, before)

    @skip_parallel  # warning is emitted on the main rank only; asserts single-rank
    def test_auto_upgrade_of_legacy_file(self):
        from bsb import BsbProvenanceUpgradeWarning
        from bsb.services import MPI

        import bsb_hdf5

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "legacy.hdf5")
            with h5py.File(path, "w") as f:
                f.attrs["bsb_hdf5_version"] = "0.0.0"
                f.attrs["bsb_version"] = "0.0.0"
                f.create_group("placement")
                f.create_group("connectivity")
                f.create_group("files")
                f.create_group("morphologies")
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                eng = bsb_hdf5.HDF5Engine(path, MPI)
            upgrade_warnings = [
                w for w in caught if issubclass(w.category, BsbProvenanceUpgradeWarning)
            ]
            self.assertEqual(len(upgrade_warnings), 1)
            md = eng.metadata
            self.assertIn("storage_id", md)
            self.assertEqual(md["state_id"], 1)
            self.assertEqual(md["engine_name"], "hdf5")


class TestFSProvenance(unittest.TestCase):
    """Verify the FileSystem engine writes & maintains the provenance bundle."""

    def _new_storage(self, path):
        from bsb.storage import Storage

        return Storage("fs", path)

    def test_create_writes_metadata_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "fsroot")
            s = self._new_storage(path)
            md = s._engine.metadata
            self.assertEqual(md.get("engine_name"), "fs")
            self.assertIn("storage_id", md)
            self.assertEqual(md["state_id"], 0)

    @skip_parallel  # asserts an exact per-rank bump count from direct calls
    def test_state_bumps(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "fsroot")
            s = self._new_storage(path)
            s._engine._bump_state()
            s._engine._bump_state()
            self.assertEqual(s._engine.state_id, 2)

    @skip_parallel  # warning + rank-local temp path; asserts single-rank
    def test_auto_upgrades_versions_txt(self):
        """Legacy roots that only have versions.txt are upgraded on open."""
        from bsb import BsbProvenanceUpgradeWarning
        from bsb.services import MPI
        from bsb.storage.fs import FileSystemEngine

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "legacy_fs")
            os.makedirs(os.path.join(path, "files"))
            os.makedirs(os.path.join(path, "file_meta"))
            with open(os.path.join(path, "versions.txt"), "w") as f:
                f.write('{"bsb": "0.0.0", "engine": "fs", "version": "0.0.0"}')
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                eng = FileSystemEngine(path, MPI)
            upgrade = [
                w for w in caught if issubclass(w.category, BsbProvenanceUpgradeWarning)
            ]
            self.assertEqual(len(upgrade), 1)
            md = eng.metadata
            self.assertIn("storage_id", md)
            self.assertEqual(md["state_id"], 1)
            self.assertFalse(
                os.path.exists(os.path.join(path, "versions.txt")),
                "versions.txt should be removed after upgrade",
            )


class TestScaffoldProvenanceAPI(unittest.TestCase):
    def test_scaffold_exposes_storage_id_state_id_provenance(self):
        from bsb.config import Configuration
        from bsb.core import Scaffold
        from bsb.storage import Storage

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "net.hdf5")
            storage = Storage("hdf5", path)
            scaffold = Scaffold(Configuration.default(), storage=storage)
            self.assertEqual(scaffold.storage_id, storage._engine.storage_id)
            self.assertIsInstance(scaffold.state_id, int)
            self.assertIn("storage_id", scaffold.provenance)


if __name__ == "__main__":
    unittest.main()
