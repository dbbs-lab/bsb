import os
import sys
import threading
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def get_data_path(*paths):
    return os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "data",
            *paths,
        )
    )


def get_config_path(file):
    return get_data_path(
        "configs",
        file + (".json" if not file.endswith(".json") else ""),
    )


def get_morphology_path(file):
    return get_data_path(
        "morphologies",
        file,
    )
