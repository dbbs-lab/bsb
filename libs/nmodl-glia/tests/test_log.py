import os
import unittest

from glia._fs import get_log_path, log


class TestLog(unittest.TestCase):
    def test_log_path_per_process(self):
        # The logfile is named after the pid, so concurrently running processes
        # never write to, or unlink, each other's file.
        self.assertEqual(f"{os.getpid()}.txt", get_log_path().name)

    def test_log(self):
        log_path = get_log_path()
        log_path.unlink(missing_ok=True)
        log("hello world")
        self.assertTrue(log_path.exists(), "Logs not created")
        self.assertIn("hello world", log_path.read_text(), "Log not logged")

    def test_exc(self):
        log_path = get_log_path()
        log_path.unlink(missing_ok=True)
        try:
            raise RuntimeError()
        except RuntimeError as e:
            log("hello world", exc=e)
        self.assertTrue(log_path.exists(), "Logs not created")
        # Check log level elevation to ERROR
        self.assertIn("ERROR] hello world", log_path.read_text(), "Exc not logged")
