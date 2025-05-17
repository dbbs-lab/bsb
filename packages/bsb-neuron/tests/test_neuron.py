import importlib
import itertools
import traceback
import unittest
from copy import copy

from arborize import define_model
from bsb.core import Scaffold
from bsb.services import MPI
from bsb.simulation import get_simulation_adapter
from bsb_test import (
    ConfigFixture,
    MorphologiesFixture,
    NetworkFixture,
    RandomStorageFixture,
)
from patch import p

from bsb_neuron.cell import ArborizedModel
from bsb_neuron.connection import TransceiverModel


def neuron_installed():
    return importlib.util.find_spec("neuron")


@unittest.skipIf(not neuron_installed(), "NEURON is not installed")
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


@unittest.skipIf(not neuron_installed(), "NEURON is not installed")
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
        compartment HH cells and ExpSyn synapses connected manually
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


@unittest.skipIf(not neuron_installed(), "NEURON is not installed")
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
        compartment HH cells and ExpSyn synapses manually connected
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


@unittest.skipIf(not neuron_installed(), "NEURON is not installed")
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
        compartment HH cells and ExpSyn synapses connected manually
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


@unittest.skipIf(not neuron_installed(), "NEURON is not installed")
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
        compartment HH cells and ExpSyn synapses connected manually with loop (within cell and cs)
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
