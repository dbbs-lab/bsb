import unittest
from pathlib import Path

from glia._fs import get_cache_path, log


class TestLog(unittest.TestCase):
    def test_log_hash(self):
        # We use the fact that Python salts hashes per session (see
        # https://docs.python.org/3/using/cmdline.html#envvar-PYTHONHASHSEED) to get a
        # a unique logfile hash per process, test this.
        self.assertEqual(id("5"), id("5"))

    def test_log(self):
        log_path = Path(get_cache_path(f"{id('5')}.txt"))
        log_path.unlink(missing_ok=True)
        log("hello world")
        self.assertTrue(log_path.exists(), "Logs not created")
        self.assertIn("hello world", log_path.read_text(), "Log not logged")

    def test_exc(self):
        log_path = Path(get_cache_path(f"{id('5')}.txt"))
        log_path.unlink(missing_ok=True)
        try:
            raise RuntimeError()
        except RuntimeError as e:
            log("hello world", exc=e)
        self.assertTrue(log_path.exists(), "Logs not created")
        # Check log level elevation to ERROR
        self.assertIn("ERROR] hello world", log_path.read_text(), "Exc not logged")
