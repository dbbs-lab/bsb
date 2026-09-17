import os
import shutil
import tempfile
import unittest

import numpy as np
from bsb import MPI, Configuration, Scaffold, read_results
from bsb.simulation.results import iter_recordings
from bsb_test import (
    NumpyTestCase,
    RandomStorageFixture,
    get_test_config,
    get_test_config_tree,
)


def _population_rate(block, device, duration):
    """
    Mean firing rate over a device's targets, in Hz.

    Spikes are recorded one train per cell, so the population's spikes are the
    trains of that device summed; cells that never fired have no train at all,
    which is why the divisor is the device's target count and not the number of
    trains.
    """
    recordings = list(iter_recordings(block, device=device))
    assert recordings, f"no recordings for device {device!r}"
    n_spikes = sum(len(recording.signal) for recording in recordings)
    # Every cell the device watched has a train, so the trains are the population.
    return n_spikes / duration * 1000.0 / len(recordings)


@unittest.skipIf(MPI.get_size() > 1, "Skipped during parallel testing.")
class TestArbor(RandomStorageFixture, unittest.TestCase, engine_name="hdf5"):
    def test_brunel(self):
        cfg = get_test_config_tree("brunel_wbsb")
        # Remove unused nest simulation
        # This way we do not have to install nest
        del cfg["simulations"]["test_nest"]
        cfg = Configuration(cfg)
        simcfg = cfg.simulations.test_arbor

        network = Scaffold(cfg, self.storage)
        network.compile()
        result = network.run_simulation("test_arbor")

        rate_ex = _population_rate(result.block, "sr_exc", simcfg.duration)
        rate_in = _population_rate(result.block, "sr_inh", simcfg.duration)

        # These are temporary circular values, taken from the output. May be incorrect.
        self.assertAlmostEqual(rate_in, 34.2, delta=1)
        self.assertAlmostEqual(rate_ex, 34.2, delta=1)


def _placement_order(positions, chunk_size):
    """
    Positions in the order a placement set holds them: grouped by chunk in order of
    chunk id, and in the order they were placed within a chunk.
    """
    chunks = np.floor_divide(positions, chunk_size).astype(np.int64)
    chunk_ids = chunks[:, 0] + chunks[:, 1] * 2**16 + chunks[:, 2] * 2**32
    return positions[np.argsort(chunk_ids, kind="stable")]


@unittest.skipIf(MPI.get_size() > 1, "Skipped during parallel testing.")
class TestRecordingsNameTheirCells(
    RandomStorageFixture, NumpyTestCase, unittest.TestCase, engine_name="hdf5"
):
    """
    A recording names its cell by cell model and placement set id, whatever id arbor
    gave it, so reading the results with the network gives back the recorded cells.
    """

    def setUp(self):
        super().setUp()
        cfg = get_test_config("chunked")
        cfg.connectivity = {}
        # Placed out of chunk order, so the placement set's order is not the order
        # given and every model but the first starts at a gid offset.
        given = np.array(cfg.placement.across_chunks.positions)[::-1]
        cfg.placement.across_chunks.positions = given.tolist()
        self.positions = _placement_order(given, cfg.network.chunk_size)
        lif = {"model_strategy": "lif", "constants": {"C_m": 250, "V_th": 20}}
        cfg.simulations.add(
            "test",
            simulator="arbor",
            duration=10,
            resolution=0.5,
            cell_models={name: lif for name in ("A", "B", "C")},
            connection_models={},
            devices={
                "by_id": {
                    "device": "spike_recorder",
                    "targetting": {"strategy": "by_id", "ids": {"B": [3, 7, 11]}},
                },
                "sphere": {
                    "device": "spike_recorder",
                    "targetting": {
                        "strategy": "sphere",
                        "origin": [45, 10, 10],
                        "radius": 20,
                    },
                },
            },
        )
        self.network = Scaffold(cfg, self.storage)
        self.network.compile()

    def _results_file(self):
        tmpdir = MPI.bcast(tempfile.mkdtemp() if not MPI.get_rank() else None)
        if not MPI.get_rank():
            self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        return os.path.join(tmpdir, "traced.nio")

    def test_recordings_trace_back_to_their_cells(self):
        filename = self._results_file()
        self.network.run_simulation("test", output_filename=filename)
        if MPI.get_rank():
            return
        results = read_results(self.network, filename)

        by_id = list(results.recordings("by_id"))
        self.assertEqual([3, 7, 11], sorted(r.target.id for r in by_id))
        for recording in by_id:
            with self.subTest(device="by_id", cell=recording.target.id):
                self.assertEqual("B", recording.target.model)
                self.assertEqual("B", recording.target.cell_type.name)
                self.assertClose(
                    self.positions[recording.target.id], recording.target.position
                )

        in_sphere = np.flatnonzero(
            np.sum((self.positions - [45, 10, 10]) ** 2, axis=1) < 20**2
        )
        self.assertEqual(2, len(in_sphere), "the sphere has to span two chunks")
        sphere = list(results.recordings("sphere"))
        for model in ("A", "B", "C"):
            with self.subTest(device="sphere", model=model):
                cells = [r.target for r in sphere if r.target.model == model]
                self.assertEqual(sorted(in_sphere), sorted(c.id for c in cells))
                for cell in cells:
                    self.assertClose(self.positions[cell.id], cell.position)
