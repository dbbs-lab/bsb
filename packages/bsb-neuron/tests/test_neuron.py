import itertools
import os
import shutil
import tempfile
import unittest
from copy import copy

import numpy as np
from bsb import MPI, Scaffold, get_simulation_adapter, read_results
from bsb_test import (
    ConfigFixture,
    MorphologiesFixture,
    NetworkFixture,
    NumpyTestCase,
    RandomStorageFixture,
)
from patch import p

from bsb_neuron.cell import ArborizedModel
from bsb_neuron.connection import TransceiverModel


class TestNeuronMinimal(
    RandomStorageFixture,
    ConfigFixture,
    NetworkFixture,
    MorphologiesFixture,
    unittest.TestCase,
    config="neuron_minimal",
    morpho_filters=["2comp"],
    engine_name="hdf5",
):
    def setUp(self):
        super().setUp()
        self.network.compile()

    def test_minimal(self):
        from neuron import h

        sim = self.network.simulations.test
        self.network.run_simulation("test")
        self.assertAlmostEqual(h.t, sim.duration, msg="sim duration incorrect")

    def test_double_sim_minimal(self):
        from neuron import h

        scaffold_copy = Scaffold(copy(self.cfg), self.storage)
        sim = self.network.simulations.test
        sim2 = scaffold_copy.simulations.test
        sim2.duration *= 2
        adapter = get_simulation_adapter(sim.simulator)
        adapter.simulate(sim, sim2)

        self.assertAlmostEqual(h.t, sim2.duration, msg="sim duration incorrect")

    def test_composition_writes_separate_blocks(self):
        """Two simulations composed in one adapter and streamed to one file are written
        as separate blocks with distinct storage keys."""
        import os
        import shutil
        import tempfile

        from neo import io

        scaffold_copy = Scaffold(copy(self.cfg), self.storage)
        sim = self.network.simulations.test
        sim2 = scaffold_copy.simulations.test
        adapter = get_simulation_adapter(sim.simulator)

        # One directory for the whole run. The ranks write parts of one file and
        # rank 0 merges them, so a directory drawn per rank would leave every other
        # rank looking for a file that was assembled somewhere else.
        tmpdir = MPI.bcast(tempfile.mkdtemp() if not MPI.get_rank() else None)
        if not MPI.get_rank():
            self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        nio_file = os.path.join(tmpdir, "composed.nio")

        adapter.simulate(sim, sim2, filename=nio_file)

        blocks = io.NixIO(nio_file, "ro").read_all_blocks()
        self.assertEqual(len(blocks), 2, "Expected one block per composed simulation")
        self.assertEqual(
            len({b.annotations["nix_name"] for b in blocks}),
            2,
            "Composed simulations must get distinct storage keys",
        )


class TestNeuronMultichunk(
    RandomStorageFixture,
    ConfigFixture,
    NetworkFixture,
    MorphologiesFixture,
    unittest.TestCase,
    config="chunked",
    morpho_filters=["2comp"],
    engine_name="hdf5",
):
    def setUp(self):
        super().setUp()
        p.parallel.gid_clear()
        for ct in self.network.cell_types.values():
            ct.spatial.morphologies = ["2comp"]
        hh_soma = {
            "cable_types": {
                "soma": {
                    "cable": {"Ra": 10, "cm": 1},
                    "mechanisms": {"pas": {}, "hh": {}},
                }
            },
            "synapse_types": {"ExpSyn": {}},
        }
        self.network.simulations.add(
            "test",
            simulator="neuron",
            duration=1000,
            resolution=0.1,
            temperature=32,
            cell_models=dict(
                A=ArborizedModel(model=hh_soma),
                B=ArborizedModel(model=hh_soma),
                C=ArborizedModel(model=hh_soma),
            ),
            connection_models=dict(
                A_to_B=TransceiverModel(synapses=[dict(synapse="ExpSyn")]),
                B_to_C=TransceiverModel(synapses=[dict(synapse="ExpSyn")]),
                C_to_A=TransceiverModel(synapses=[dict(synapse="ExpSyn")]),
            ),
            devices=dict(),
        )
        self.network.compile()

    def test_4ch_manual(self):
        """
        Tests runnability of the NEURON adapter with 4 chunks filled with 12x3 single
        compartment HH cells and ExpSyn synapses connected manually.
        """
        sim = self.network.simulations.test
        adapter = get_simulation_adapter(sim.simulator)
        simdata = adapter.prepare(sim)
        transmitting_cells = sorted(
            itertools.chain.from_iterable(
                MPI.allgather(
                    [
                        (model.name, cell.id, transmitter.gid)
                        for model, pop in simdata.populations.items()
                        for cell in pop
                        if (
                            transmitter := getattr(cell.sections[0], "_transmitter", None)
                        )
                    ]
                )
            )
        )
        receiving_cells = sorted(
            itertools.chain.from_iterable(
                MPI.allgather(
                    [
                        (model.name, cell.id, synapse.gid)
                        for model, pop in simdata.populations.items()
                        for cell in pop
                        for synapse in getattr(cell.sections[0], "synapses", [])
                    ]
                )
            )
        )
        self.assertEqual(
            [
                # A to B
                ("A", 0, 0),
                ("A", 1, 1),
                ("A", 3, 2),
                ("A", 5, 3),
                # B to C
                ("B", 5, 4),
                # C to A
                ("C", 1, 5),
                ("C", 5, 6),
            ],
            transmitting_cells,
        )
        self.assertEqual(
            [
                # C to A
                ("A", 1, 6),
                ("A", 5, 5),
                ("A", 11, 6),
                # A to B
                ("B", 0, 0),
                ("B", 0, 1),
                ("B", 2, 3),
                ("B", 3, 1),
                ("B", 8, 2),
                # B to C
                ("C", 9, 4),
                ("C", 10, 4),
                ("C", 11, 4),
            ],
            receiving_cells,
        )


class TestNeuronSmallChunk(
    RandomStorageFixture,
    ConfigFixture,
    NetworkFixture,
    MorphologiesFixture,
    unittest.TestCase,
    config="chunked",
    morpho_filters=["2comp"],
    engine_name="hdf5",
):
    def setUp(self):
        super().setUp()
        p.parallel.gid_clear()
        self.network.network.chunk_size = [10, 10, 10]
        for ct in self.network.cell_types.values():
            ct.spatial.morphologies = ["2comp"]
        hh_soma = {
            "cable_types": {
                "soma": {
                    "cable": {"Ra": 10, "cm": 1},
                    "mechanisms": {"pas": {}, "hh": {}},
                }
            },
            "synapse_types": {"ExpSyn": {}},
        }
        self.network.simulations.add(
            "test",
            simulator="neuron",
            duration=1000,
            resolution=0.1,
            temperature=32,
            cell_models=dict(
                A=ArborizedModel(model=hh_soma),
                B=ArborizedModel(model=hh_soma),
                C=ArborizedModel(model=hh_soma),
            ),
            connection_models=dict(
                A_to_B=TransceiverModel(synapses=[dict(synapse="ExpSyn")]),
                B_to_C=TransceiverModel(synapses=[dict(synapse="ExpSyn")]),
                C_to_A=TransceiverModel(synapses=[dict(synapse="ExpSyn")]),
            ),
            devices=dict(),
        )
        self.network.compile()

    def test_smallch_manual(self):
        """
        Tests runnability of the NEURON adapter with 500 chunks filled with 12x3 single
        compartment HH cells and ExpSyn synapses manually connected.
        """
        sim = self.network.simulations.test
        adapter = get_simulation_adapter(sim.simulator)
        simdata = adapter.prepare(sim)
        transmitting_cells = sorted(
            itertools.chain.from_iterable(
                MPI.allgather(
                    [
                        (model.name, cell.id, transmitter.gid)
                        for model, pop in simdata.populations.items()
                        for cell in pop
                        if (
                            transmitter := getattr(cell.sections[0], "_transmitter", None)
                        )
                    ]
                )
            )
        )
        receiving_cells = sorted(
            itertools.chain.from_iterable(
                MPI.allgather(
                    [
                        (model.name, cell.id, synapse.gid)
                        for model, pop in simdata.populations.items()
                        for cell in pop
                        for synapse in getattr(cell.sections[0], "synapses", [])
                    ]
                )
            )
        )
        self.assertEqual(
            [
                # A to B
                ("A", 0, 0),
                ("A", 1, 1),
                ("A", 3, 2),
                ("A", 5, 3),
                # B to C
                ("B", 5, 4),
                # C to A
                ("C", 1, 5),
                ("C", 5, 6),
            ],
            transmitting_cells,
        )
        self.assertEqual(
            [
                # C to A
                ("A", 1, 6),
                ("A", 5, 5),
                ("A", 11, 6),
                # A to B
                ("B", 0, 0),
                ("B", 0, 1),
                ("B", 2, 3),
                ("B", 3, 1),
                ("B", 8, 2),
                # B to C
                ("C", 9, 4),
                ("C", 10, 4),
                ("C", 11, 4),
            ],
            receiving_cells,
        )


class TestNeuronMultiBranch(
    RandomStorageFixture,
    ConfigFixture,
    NetworkFixture,
    MorphologiesFixture,
    unittest.TestCase,
    config="multi",
    morpho_filters=["3branch"],
    engine_name="hdf5",
):
    def setUp(self):
        super().setUp()
        p.parallel.gid_clear()
        for ct in self.network.cell_types.values():
            ct.spatial.morphologies = ["3branch"]
        hh_soma = {
            "cable_types": {
                "soma": {
                    "cable": {"Ra": 10, "cm": 1},
                    "mechanisms": {"pas": {}, "hh": {}},
                }
            },
            "synapse_types": {"ExpSyn": {}},
        }
        self.network.simulations.add(
            "test",
            simulator="neuron",
            duration=1000,
            resolution=0.1,
            temperature=32,
            cell_models=dict(
                A=ArborizedModel(model=hh_soma),
                B=ArborizedModel(model=hh_soma),
                C=ArborizedModel(model=hh_soma),
            ),
            connection_models=dict(
                A_to_B=TransceiverModel(synapses=[dict(synapse="ExpSyn")]),
                B_to_C=TransceiverModel(synapses=[dict(synapse="ExpSyn")]),
                C_to_A=TransceiverModel(synapses=[dict(synapse="ExpSyn")]),
            ),
            devices=dict(),
        )
        self.network.compile()

    def test_500ch_multibranch_manualconn(self):
        """
        Tests runnability of the NEURON adapter with 500 chunks filled with 12x3 single
        compartment HH cells and ExpSyn synapses connected manually.
        """
        sim = self.network.simulations.test
        adapter = get_simulation_adapter(sim.simulator)
        simdata = adapter.prepare(sim)
        transmitting_cells = sorted(
            itertools.chain.from_iterable(
                MPI.allgather(
                    [
                        (model.name, cell.id, i_sec, transmitter.gid)
                        for model, pop in simdata.populations.items()
                        for cell in pop
                        for i_sec, sec_i in enumerate(cell.sections)
                        if (
                            transmitter := getattr(
                                cell.sections[i_sec], "_transmitter", None
                            )
                        )
                    ]
                )
            )
        )
        receiving_cells = sorted(
            itertools.chain.from_iterable(
                MPI.allgather(
                    [
                        (model.name, cell.id, i_sec, synapse.gid)
                        for model, pop in simdata.populations.items()
                        for cell in pop
                        for i_sec, sec_i in enumerate(cell.sections)
                        for synapse in getattr(cell.sections[i_sec], "synapses", [])
                    ]
                )
            )
        )
        self.assertEqual(
            [
                # A
                ("A", 0, 0, 0),
                ("A", 0, 1, 1),
                ("A", 3, 1, 2),
                ("A", 5, 0, 3),
                # B
                ("B", 5, 0, 4),
                # C
                ("C", 1, 0, 5),
                ("C", 5, 0, 6),
            ],
            transmitting_cells,
        )
        self.assertEqual(
            [
                # C to A
                ("A", 1, 0, 6),
                ("A", 5, 0, 5),
                ("A", 11, 0, 6),
                # A to B
                ("B", 3, 0, 0),
                ("B", 3, 0, 1),
                ("B", 5, 0, 2),
                ("B", 8, 0, 2),
                ("B", 10, 1, 3),
                # B to C
                ("C", 9, 0, 4),
                ("C", 10, 1, 4),
                ("C", 11, 0, 4),
            ],
            receiving_cells,
        )


class TestNeuronMultiBranchLoop(
    RandomStorageFixture,
    ConfigFixture,
    NetworkFixture,
    MorphologiesFixture,
    unittest.TestCase,
    config="complete",
    morpho_filters=["3branch"],
    engine_name="hdf5",
):
    def setUp(self):
        super().setUp()
        p.parallel.gid_clear()
        for ct in self.network.cell_types.values():
            ct.spatial.morphologies = ["3branch"]
        hh_soma = {
            "cable_types": {
                "soma": {
                    "cable": {"Ra": 10, "cm": 1},
                    "mechanisms": {"pas": {}, "hh": {}},
                }
            },
            "synapse_types": {"ExpSyn": {}},
        }
        self.network.simulations.add(
            "test",
            simulator="neuron",
            duration=1000,
            resolution=0.1,
            temperature=32,
            cell_models=dict(
                A=ArborizedModel(model=hh_soma),
                B=ArborizedModel(model=hh_soma),
                C=ArborizedModel(model=hh_soma),
            ),
            connection_models=dict(
                A_to_A=TransceiverModel(synapses=[dict(synapse="ExpSyn")]),
                A_to_B=TransceiverModel(synapses=[dict(synapse="ExpSyn")]),
                B_to_C=TransceiverModel(synapses=[dict(synapse="ExpSyn")]),
                C_to_A=TransceiverModel(synapses=[dict(synapse="ExpSyn")]),
                C_to_B=TransceiverModel(synapses=[dict(synapse="ExpSyn")]),
            ),
            devices=dict(),
        )
        self.network.compile()

    def test_500ch_manualloop(self):
        """
        Tests runnability of the NEURON adapter with 500 chunks filled with 12x3 single
        compartment HH cells and ExpSyn synapses connected manually with loop (within cell
        and cs)
        """
        sim = self.network.simulations.test
        adapter = get_simulation_adapter(sim.simulator)
        simdata = adapter.prepare(sim)
        transmitting_cells = sorted(
            itertools.chain.from_iterable(
                MPI.allgather(
                    [
                        (model.name, cell.id, i_sec, transmitter.gid)
                        for model, pop in simdata.populations.items()
                        for cell in pop
                        for i_sec, sec_i in enumerate(cell.sections)
                        if (
                            transmitter := getattr(
                                cell.sections[i_sec], "_transmitter", None
                            )
                        )
                    ]
                )
            )
        )
        receiving_cells = sorted(
            itertools.chain.from_iterable(
                MPI.allgather(
                    [
                        (model.name, cell.id, i_sec, synapse.gid)
                        for model, pop in simdata.populations.items()
                        for cell in pop
                        for i_sec, sec_i in enumerate(cell.sections)
                        for synapse in getattr(cell.sections[i_sec], "synapses", [])
                    ]
                )
            )
        )
        self.assertEqual(
            [
                # A
                ("A", 0, 0, 0),
                ("A", 0, 1, 1),
                ("A", 1, 0, 2),
                ("A", 3, 0, 3),
                ("A", 3, 1, 4),
                ("A", 5, 0, 5),
                # B
                ("B", 5, 0, 6),
                # C
                ("C", 1, 0, 7),
                ("C", 5, 0, 8),
            ],
            transmitting_cells,
        )
        self.assertEqual(
            [
                ("A", 0, 1, 0),  # A to A
                ("A", 1, 0, 8),  # C to A
                ("A", 3, 0, 2),  # A to A
                ("A", 5, 0, 7),  # C to A
                ("A", 7, 1, 0),  # A to A
                ("A", 7, 1, 4),  # A to A
                ("A", 11, 0, 8),  # C to A
                ("B", 1, 0, 8),  # C to B
                # A to B
                ("B", 3, 0, 0),
                ("B", 3, 0, 1),
                ("B", 5, 0, 3),
                ("B", 5, 0, 7),  # C to B
                ("B", 8, 0, 3),  # A to B
                ("B", 10, 0, 5),  # A to B
                ("B", 11, 0, 8),  # C to B
                # B to C
                ("C", 9, 0, 6),
                ("C", 10, 0, 6),
                ("C", 11, 0, 6),
            ],
            receiving_cells,
        )


def _placement_order(positions, chunk_size):
    """
    Positions in the order a placement set holds them: grouped by chunk in order of
    chunk id, and in the order they were placed within a chunk.
    """
    chunks = np.floor_divide(positions, chunk_size).astype(np.int64)
    chunk_ids = chunks[:, 0] + chunks[:, 1] * 2**16 + chunks[:, 2] * 2**32
    return positions[np.argsort(chunk_ids, kind="stable")]


class TestRecordingsNameTheirCells(
    RandomStorageFixture,
    ConfigFixture,
    NetworkFixture,
    MorphologiesFixture,
    NumpyTestCase,
    unittest.TestCase,
    config="chunked",
    morpho_filters=["2comp"],
    engine_name="hdf5",
):
    """
    A recording names its cell by cell model and placement set id, so reading the
    results with the network gives back the recorded cells.
    """

    def setUp(self):
        super().setUp()
        p.parallel.gid_clear()
        # Placed out of chunk order, so the placement set's order is not the order
        # given.
        placement = self.network.placement.across_chunks
        given = np.array(placement.positions)[::-1]
        placement.positions = given.tolist()
        self.positions = _placement_order(given, self.network.network.chunk_size)
        for ct in self.network.cell_types.values():
            ct.spatial.morphologies = ["2comp"]
        hh_soma = {
            "cable_types": {
                "soma": {
                    "cable": {"Ra": 10, "cm": 1},
                    "mechanisms": {"pas": {}, "hh": {}},
                }
            },
            "synapse_types": {"ExpSyn": {}},
        }
        self.network.simulations.add(
            "test",
            simulator="neuron",
            duration=5,
            resolution=0.1,
            temperature=32,
            cell_models={name: ArborizedModel(model=hh_soma) for name in "ABC"},
            connection_models={
                "A_to_B": TransceiverModel(synapses=[dict(synapse="ExpSyn")])
            },
            devices={
                "synapses": {
                    "device": "synapse_recorder",
                    "locations": {"strategy": "everywhere"},
                    "targetting": {"strategy": "by_id", "ids": {"B": [0, 8]}},
                },
                "by_id": {
                    "device": "voltage_recorder",
                    "targetting": {"strategy": "by_id", "ids": {"B": [3, 7, 11]}},
                },
                "sphere": {
                    "device": "voltage_recorder",
                    "targetting": {
                        "strategy": "sphere",
                        "origin": [45, 10, 10],
                        "radius": 20,
                    },
                },
            },
        )
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
        self.assertEqual([3, 7, 11], sorted(r.target.cell.id for r in by_id))
        for recording in by_id:
            cell = recording.target.cell
            with self.subTest(device="by_id", cell=cell.id):
                self.assertEqual(
                    ("point", "record"), (recording.kind, recording.direction)
                )
                self.assertEqual(
                    (0, 0), (recording.target.branch, recording.target.point)
                )
                self.assertEqual("B", cell.model)
                self.assertEqual("B", cell.cell_type.name)
                self.assertClose(self.positions[cell.id], cell.position)

        in_sphere = np.flatnonzero(
            np.sum((self.positions - [45, 10, 10]) ** 2, axis=1) < 20**2
        )
        self.assertEqual(2, len(in_sphere), "the sphere has to span two chunks")
        sphere = list(results.recordings("sphere"))
        for model in ("A", "B", "C"):
            with self.subTest(device="sphere", model=model):
                cells = [r.target.cell for r in sphere if r.target.cell.model == model]
                self.assertEqual(sorted(in_sphere), sorted(c.id for c in cells))
                for cell in cells:
                    self.assertClose(self.positions[cell.id], cell.position)

        # The connectivity is fixed: A 0 and A 1 onto B 0, and A 3 onto B 8.
        synapses = list(results.recordings("synapses"))
        self.assertEqual(
            [(0, 0), (0, 1), (8, 3)],
            sorted((r.target.cell.id, r.target.presynaptic.id) for r in synapses),
        )
        for recording in synapses:
            with self.subTest(device="synapses", cell=recording.target.cell.id):
                self.assertEqual("synapse", recording.kind)
                self.assertEqual("ExpSyn", recording.target.synapse_type)
                self.assertEqual("A", recording.target.presynaptic.model)
                self.assertClose(
                    self.positions[recording.target.presynaptic.id],
                    recording.target.presynaptic.position,
                )
