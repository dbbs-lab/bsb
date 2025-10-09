import unittest
from unittest.mock import patch

import nest
import numpy as np
from bsb import BootError, CastError, ConfigurationError
from bsb.config import Configuration
from bsb.core import Scaffold
from bsb.services import MPI
from bsb_test import NumpyTestCase, RandomStorageFixture, get_test_config
from nest.lib.hl_api_exceptions import NESTErrors
from scipy.optimize import curve_fit

from bsb_nest import NestAdapter


def _conf_single_cell():
    return Configuration(
        {
            "name": "test",
            "storage": {"engine": "hdf5"},
            "network": {"x": 100, "y": 100, "z": 100},
            "partitions": {"B": {"type": "layer", "thickness": 1}},
            "cell_types": {"A": {"spatial": {"radius": 1, "count": 1}}},
            "placement": {
                "placement_A": {
                    "strategy": "bsb.placement.strategy.FixedPositions",
                    "cell_types": ["A"],
                    "partitions": ["B"],
                    "positions": [[1, 1, 1]],
                }
            },
            "connectivity": {},
            "after_connectivity": {},
            "simulations": {},
        }
    )


def _conf_two_cells():
    return Configuration(
        {
            "name": "test",
            "storage": {"engine": "hdf5"},
            "network": {"x": 1, "y": 1, "z": 1},
            "partitions": {"B": {"type": "layer", "thickness": 1}},
            "cell_types": {
                "A": {"spatial": {"radius": 1, "count": 1}},
                "C": {"spatial": {"radius": 1, "count": 1}},
            },
            "placement": {
                "placement_A": {
                    "strategy": "bsb.placement.strategy.FixedPositions",
                    "cell_types": ["A"],
                    "partitions": ["B"],
                    "positions": [[1, 1, 1]],
                },
                "placement_C": {
                    "strategy": "bsb.placement.strategy.FixedPositions",
                    "cell_types": ["C"],
                    "partitions": ["B"],
                    "positions": [[0, 0, 0]],
                },
            },
            "connectivity": {
                "C_to_A": {
                    "strategy": "bsb.connectivity.AllToAll",
                    "presynaptic": {"cell_types": ["C"]},
                    "postsynaptic": {"cell_types": ["A"]},
                }
            },
            "after_connectivity": {},
            "simulations": {},
        }
    )


@unittest.skipIf(MPI.get_size() > 1, "Skipped during parallel testing.")
class TestNest(
    RandomStorageFixture, NumpyTestCase, unittest.TestCase, engine_name="hdf5"
):
    def test_gif_pop_psc_exp(self):
        """Mimics test_gif_pop_psc_exp of NEST's test suite to validate the adapter."""
        pop_size = 500

        cfg = get_test_config("gif_pop_psc_exp")
        sim_cfg = cfg.simulations.test_nest
        sim_cfg.resolution = 0.5
        sim_cfg.cell_models.gif_pop_psc_exp.constants["N"] = pop_size

        network = Scaffold(cfg, self.storage)
        network.compile()

        simulation = None
        vm = None
        nspike = None

        def probe(_, sim, data):
            # Probe and steal some local refs to data that's otherwise encapsulated :)
            nonlocal vm, simulation
            simulation = sim

            # Get the important information out of the sim/data
            cell_m = sim.cell_models.gif_pop_psc_exp
            conn_m = sim.connection_models.gif_pop_psc_exp
            pop = data.populations[cell_m]
            syn = data.connections[conn_m]

            # Add a voltmeter
            vm = nest.Create(
                "voltmeter",
                params={"record_from": ["n_events"], "interval": sim.resolution},
            )
            nest.Connect(vm, pop)

            # Add a spying recorder
            def spy(_):
                nonlocal nspike

                start_time = 1000
                start_step = int(start_time / simulation.resolution)
                nspike = vm.events["n_events"][start_step:]

            data.result.create_recorder(spy)

            # Test node parameter transfer
            for param, value in {
                "V_reset": 0.0,
                "V_T_star": 10.0,
                "E_L": 0.0,
                "Delta_V": 2.0,
                "C_m": 250.0,
                "tau_m": 20.0,
                "t_ref": 4.0,
                "I_e": 500.0,
                "lambda_0": 10.0,
                "tau_syn_in": 2.0,
                "tau_sfa": (500.0,),
                "q_sfa": (1.0,),
            }.items():
                with self.subTest(param=param, value=value):
                    self.assertEqual(value, pop.get(param))

            # Test synapse parameter transfer
            for param, value in (("weight", -6.25), ("delay", 1)):
                with self.subTest(param=param, value=value):
                    self.assertEqual(value, syn.get(param))

        network.simulations.test_nest.post_prepare.append(probe)
        network.run_simulation("test_nest")

        mean_nspike = np.mean(nspike)
        mean_rate = mean_nspike / pop_size / simulation.resolution * 1000.0

        var_nspike = np.var(nspike)
        var_nspike = var_nspike / pop_size / simulation.resolution * 1000.0
        var_rate = var_nspike / pop_size / simulation.resolution * 1000.0

        err_mean = 1.0
        err_var = 6.0
        expected_rate = 22.0
        expected_var = 102.0

        self.assertGreaterEqual(err_mean, abs(mean_rate - expected_rate))
        self.assertGreaterEqual(err_var, var_rate - expected_var)

    @patch("bsb_hdf5.connectivity_set.ConnectivitySet.get_local_chunks")
    def test_regression_issue_9(self, get_content_mock):
        # Override get_local_chunks to test empty connection sets
        get_content_mock.return_value = []
        cfg = get_test_config("gif_pop_psc_exp")
        # we delete the NEST connectivity rule
        cfg.simulations["test_nest"].connection_models["gif_pop_psc_exp"].rule = None
        network = Scaffold(cfg, self.storage)
        network.compile()
        # The simulation should run despite the absence of connections
        network.run_simulation("test_nest")

    def test_brunel(self):
        cfg = get_test_config("brunel")
        simcfg = cfg.simulations.test_nest

        network = Scaffold(cfg, self.storage)
        network.compile()
        result = network.run_simulation("test_nest")

        spiketrains = result.block.segments[0].spiketrains
        sr_exc, sr_inh = None, None
        for st in spiketrains:
            if st.annotations["device"] == "sr_exc":
                sr_exc = st
            elif st.annotations["device"] == "sr_inh":
                sr_inh = st

        self.assertIsNotNone(sr_exc)
        self.assertIsNotNone(sr_inh)

        rate_ex = len(sr_exc) / simcfg.duration * 1000.0 / sr_exc.annotations["pop_size"]
        rate_in = len(sr_inh) / simcfg.duration * 1000.0 / sr_inh.annotations["pop_size"]

        self.assertAlmostEqual(rate_in, 50, delta=1)
        self.assertAlmostEqual(rate_ex, 50, delta=1)

    def test_brunel_with_conn(self):
        cfg = get_test_config("brunel_wbsb")
        simcfg = cfg.simulations.test_nest

        network = Scaffold(cfg, self.storage)
        network.compile()
        result = network.run_simulation("test_nest")

        spiketrains = result.block.segments[0].spiketrains
        sr_exc, sr_inh = None, None
        for st in spiketrains:
            if st.annotations["device"] == "sr_exc":
                sr_exc = st
            elif st.annotations["device"] == "sr_inh":
                sr_inh = st

        self.assertIsNotNone(sr_exc)
        self.assertIsNotNone(sr_inh)

        rate_ex = len(sr_exc) / simcfg.duration * 1000.0 / sr_exc.annotations["pop_size"]
        rate_in = len(sr_inh) / simcfg.duration * 1000.0 / sr_inh.annotations["pop_size"]

        self.assertAlmostEqual(rate_in, 50, delta=1)
        self.assertAlmostEqual(rate_ex, 50, delta=1)

    def test_iaf_cond_alpha(self):
        """
        Create an iaf_cond_alpha in NEST, and with the BSB, with a base current, and check
        spike times.
        """
        nest.ResetKernel()
        nest.resolution = 0.1
        A = nest.Create("iaf_cond_alpha", 1, params={"I_e": 260.0})
        spikeA = nest.Create("spike_recorder")
        nest.Connect(A, spikeA)
        nest.Simulate(1000.0)

        spike_times_nest = spikeA.get("events")["times"]

        duration = 1000
        resolution = 0.1
        cfg = _conf_single_cell()
        cfg.simulations = {
            "test": {
                "simulator": "nest",
                "duration": duration,
                "resolution": resolution,
                "cell_models": {
                    "A": {
                        "model": "iaf_cond_alpha",
                        "constants": {"I_e": 260.0},
                    }
                },
                "connection_models": {},
                "devices": {
                    "record_A_spikes": {
                        "device": "spike_recorder",
                        "delay": 0.5,
                        "targetting": {
                            "strategy": "cell_model",
                            "cell_models": ["A"],
                        },
                    },
                    "voltmeter_A": {
                        "device": "multimeter",
                        "delay": resolution,
                        "properties": ["V_m"],
                        "units": ["mV"],
                        "targetting": {
                            "strategy": "cell_model",
                            "cell_models": ["A"],
                        },
                    },
                },
            }
        }
        netw = Scaffold(cfg, self.storage)
        netw.compile()
        results = netw.run_simulation("test")
        spike_times_bsb = results.spiketrains[0]
        self.assertTrue(np.unique(spike_times_bsb.array_annotations["senders"]) == 1)
        membrane_potentials = results.analogsignals[0]
        # last time point is not recorded because of recorder delay.
        self.assertTrue(len(membrane_potentials) == duration / resolution - 1)
        self.assertTrue(membrane_potentials.annotations["cell_id"] == 1)
        defaults = nest.GetDefaults("iaf_cond_alpha")
        # since current injected is positive, the V_m should be clamped between default
        # initial V_m = -70mV and spike threshold V_th = -55 mV
        self.assertAll(
            (membrane_potentials <= defaults["V_th"])
            * (membrane_potentials >= defaults["V_m"])
        )
        self.assertClose(np.array(spike_times_nest), np.array(spike_times_bsb))

    def test_multimeter_errors(self):
        cfg = get_test_config("gif_pop_psc_exp")
        sim_cfg = cfg.simulations.test_nest
        sim_cfg.devices.update(
            {
                "voltmeter": {
                    "device": "multimeter",
                    "delay": 0.1,
                    "properties": ["V_m", "I_syn"],
                    "units": ["mV"],
                    "targetting": {
                        "strategy": "cell_model",
                        "cell_models": ["gif_pop_psc_exp"],
                    },
                },
            }
        )
        with self.assertRaises(BootError):
            Scaffold(cfg, self.storage)

        sim_cfg.devices.update(
            {
                "voltmeter": {
                    "device": "multimeter",
                    "delay": 0.1,
                    "properties": ["V_m"],
                    "units": ["bla"],
                    "targetting": {
                        "strategy": "cell_model",
                        "cell_models": ["gif_pop_psc_exp"],
                    },
                },
            }
        )
        with self.assertRaises(ConfigurationError):
            Scaffold(cfg, self.storage)

    def test_dc_generator(self):
        duration = 100
        resolution = 0.1
        cfg = _conf_single_cell()
        cfg.simulations = {
            "test": {
                "simulator": "nest",
                "duration": duration,
                "resolution": resolution,
                "cell_models": {
                    "A": {
                        "model": "iaf_cond_alpha",
                        "constants": {
                            "V_reset": -70,  # V_m, E_L and V_reset are the same
                        },
                    }
                },
                "connection_models": {},
                "devices": {
                    "dc_generator": {
                        "device": "dc_generator",
                        "delay": resolution,
                        "weight": 1.0,
                        "amplitude": 200,  # Low enough so the neuron does not spike
                        "start": 50,
                        "stop": 60,
                        "targetting": {
                            "strategy": "cell_model",
                            "cell_models": ["A"],
                        },
                    },
                    "voltmeter_A": {
                        "device": "multimeter",
                        "delay": resolution,
                        "properties": ["V_m"],
                        "units": ["mV"],
                        "targetting": {
                            "strategy": "cell_model",
                            "cell_models": ["A"],
                        },
                    },
                },
            }
        }
        netw = Scaffold(cfg, self.storage)
        netw.compile()
        results = netw.run_simulation("test")
        v_ms = np.array(results.analogsignals[0])[:, 0]
        self.assertAll(v_ms[: int(50 / resolution) + 1] == -70)
        self.assertAll(
            v_ms[int(50 / resolution) + 1 : int(60 / resolution) + 1] > -70,
            "Current injected should raise membrane potential",
        )

    def test_nest_randomness(self):
        nest.ResetKernel()
        nest.resolution = 0.1
        nest.rng_seed = 1234
        # gif_cond_exp implements a random spiking process.
        # So it's perfect to test the seed
        A = nest.Create(
            "gif_cond_exp",
            1,
            params={"I_e": 200.0, "V_m": nest.random.normal(mean=-70, std=20.0)},
        )
        spikeA = nest.Create("spike_recorder")
        nest.Connect(A, spikeA)
        nest.Simulate(1000.0)
        spike_times_nest = spikeA.get("events")["times"]

        conf = _conf_single_cell()
        conf.simulations = {
            "test": {
                "simulator": "nest",
                "duration": 1000,
                "resolution": 0.1,
                "seed": 1234,
                "cell_models": {
                    "A": {
                        "model": "gif_cond_exp",
                        "constants": {
                            "I_e": 200.0,
                            "V_m": {
                                "distribution": "normal",
                                "mean": -70,
                                "std": 20.0,
                            },
                        },
                    }
                },
                "connection_models": {},
                "devices": {
                    "record_A_spikes": {
                        "device": "spike_recorder",
                        "delay": 0.5,
                        "targetting": {
                            "strategy": "cell_model",
                            "cell_models": ["A"],
                        },
                    }
                },
            }
        }
        cfg = Configuration(conf)
        netw = Scaffold(cfg, self.storage)
        netw.compile()
        results = netw.run_simulation("test")
        spike_times_bsb = results.spiketrains[0]
        self.assertClose(np.array(spike_times_nest), np.array(spike_times_bsb))
        self.assertEqual(
            cfg.__tree__()["simulations"]["test"]["cell_models"]["A"]["constants"]["V_m"],
            {
                "distribution": "normal",
                "mean": -70,
                "std": 20.0,
            },
        )

    def test_unknown_distribution(self):
        conf = {
            "name": "test",
            "storage": {"engine": "hdf5"},
            "network": {"x": 1, "y": 1, "z": 1},
            "partitions": {"B": {"type": "layer", "thickness": 1}},
            "cell_types": {"A": {"spatial": {"radius": 1, "count": 1}}},
            "placement": {
                "placement_A": {
                    "strategy": "bsb.placement.strategy.FixedPositions",
                    "cell_types": ["A"],
                    "partitions": ["B"],
                    "positions": [[1, 1, 1]],
                }
            },
            "connectivity": {},
            "after_connectivity": {},
            "simulations": {
                "test": {
                    "simulator": "nest",
                    "duration": 1000,
                    "resolution": 0.1,
                    "cell_models": {
                        "A": {
                            "model": "gif_cond_exp",
                            "constants": {
                                "I_e": 200.0,
                                "V_m": {
                                    "distribution": "bean",
                                    "mean": -70,
                                    "std": 20.0,
                                },
                            },
                        }
                    },
                    "connection_models": {},
                    "devices": {},
                }
            },
        }
        with self.assertRaises(CastError):
            Configuration(conf)

    def test_receptor_types(self):
        duration = 100
        resolution = 0.1
        cfg = _conf_single_cell()
        cfg.simulations = {
            "test": {
                "simulator": "nest",
                "duration": duration,
                "resolution": resolution,
                "seed": 1234,
                "cell_models": {
                    "A": {
                        "model": "aeif_cond_alpha_multisynapse",
                        "constants": {
                            "V_reset": -70.6,  # V_m, E_L and V_reset are the same
                            "a": 0,  # Deactivate adaptation
                            "b": 0,
                            "E_rev": [0.0, -80.0],  # Create 2 postsynaptic receptors
                            "tau_syn": [4.0, 2.0],
                        },
                    }
                },
                "connection_models": {},
                "devices": {
                    "spike_gen1": {
                        "device": "poisson_generator",
                        "delay": resolution,
                        "weight": 10.0,
                        "rate": 300,  # ~3 spikes during stim interval
                        "start": 50.0,
                        "stop": 60.0,
                        "receptor_type": 1,
                        "targetting": {
                            "strategy": "cell_model",
                            "cell_models": ["A"],
                        },
                    },
                    "spike_gen2": {  # test other receptor_type
                        "device": "poisson_generator",
                        "delay": resolution,
                        "weight": 10.0,
                        "rate": 300,  # ~3 spikes during stim interval
                        "start": 90.0,  # leave some time to rest between stims
                        "receptor_type": 2,
                        "targetting": {
                            "strategy": "cell_model",
                            "cell_models": ["A"],
                        },
                    },
                    "voltmeter_A": {
                        "device": "multimeter",
                        "delay": resolution,
                        "properties": ["V_m"],
                        "units": ["mV"],
                        "targetting": {
                            "strategy": "cell_model",
                            "cell_models": ["A"],
                        },
                    },
                },
            }
        }
        netw = Scaffold(cfg, self.storage)
        netw.compile()
        results = netw.run_simulation("test")
        v_ms = np.array(results.analogsignals[0])[:, 0]
        self.assertAll(v_ms[: int(50 / resolution) + 1] + 70.6 < 1e-3)
        self.assertAll(
            v_ms[int(50 / resolution) + 1 : int(60 / resolution) + 1] >= -70.6,
            "First Poisson stimulus should raise membrane potential",
        )
        self.assertAll(
            v_ms[int(90 / resolution) + 1 :] <= v_ms[int(90 / resolution) + 1],
            "Second Poisson stimulus should lower membrane potential",
        )

    def test_error_receptor_type(self):
        duration = 100
        resolution = 0.1
        cfg = _conf_single_cell()
        cfg.simulations = {
            "test": {
                "simulator": "nest",
                "duration": duration,
                "resolution": resolution,
                "cell_models": {
                    "A": {
                        "model": "aeif_cond_alpha_multisynapse",
                    },
                },
                "connection_models": {},
                "devices": {
                    "spike_gen1": {
                        "device": "poisson_generator",
                        "weight": 1.0,
                        "delay": resolution,
                        "rate": 10.0,
                        "receptor_type": 2,  # should fail
                        "targetting": {
                            "strategy": "cell_model",
                            "cell_models": ["A"],
                        },
                    },
                },
            }
        }
        netw = Scaffold(cfg, self.storage)
        netw.compile()
        with self.assertRaises(NESTErrors.IncompatibleReceptorType):
            netw.run_simulation("test")

    def test_sinusoidal_poisson_generator(self):
        duration = 100
        resolution = 0.1
        cfg = _conf_single_cell()
        cfg.simulations = {
            "test": {
                "simulator": "nest",
                "duration": duration,
                "resolution": resolution,
                "seed": 1234,
                "cell_models": {
                    "A": {
                        "model": "iaf_cond_alpha",
                        "constants": {
                            "V_reset": -70,  # V_m, E_L and V_reset are the same
                        },
                    }
                },
                "connection_models": {},
                "devices": {},
            }
        }
        dict_spike_gen = {
            "device": "sinusoidal_poisson_generator",
            "delay": resolution,
            "weight": 1.0,
            "rate": 1000.0,  # ~ 100 spikes during sim.
            "amplitude": 1000,
            "frequency": 20,  # 2 periods during sim.
            "phase": 2,
            "targetting": {
                "strategy": "cell_model",
                "cell_models": ["A"],
            },
        }
        nb_gen = 100
        for i in range(nb_gen):  # Add multiple generators to check randomness
            cfg.simulations["test"].devices[f"spike_gen{i}"] = dict_spike_gen
        netw = Scaffold(cfg, self.storage)
        netw.compile()

        results = netw.run_simulation("test")
        spike_times = np.array(np.concatenate(results.spiketrains))
        self.assertAlmostEqual(
            100 * nb_gen,
            len(spike_times),
            delta=nb_gen,
            msg="Roughly 100 spikes produced per generator",
        )
        counts, bins = np.histogram(
            spike_times, bins=np.linspace(0, 100, 101, endpoint=True)
        )

        def fit_sinus(x, y):
            # perform a first guess with Fourier
            ff = np.fft.fftfreq(len(x), (x[1] - x[0]))
            Fy = abs(np.fft.fft(y))
            guess_freq = abs(ff[np.argmax(Fy[1:]) + 1])  # don't take fr=0.
            guess_amp = np.sqrt(np.std(y) * 2.0)
            guess_offset = np.mean(y)
            guess = np.array([guess_amp, guess_freq, 0.0, guess_offset])
            # actual fit
            params, covariance = curve_fit(
                lambda t, f, a, p, b: a * np.sin(2 * np.pi * f * t + p) + b,
                x,
                y,
                p0=guess,
            )
            return params

        params = fit_sinus(bins[:-1] / 1e3, counts)
        self.assertAlmostEqual(20, params[0], delta=0.2)
        self.assertAlmostEqual(nb_gen, params[1], delta=2)
        self.assertAlmostEqual(nb_gen, params[3], delta=1)

    def test_error_sinusoidal_poisson_generator(self):
        duration = 100
        resolution = 0.1
        cfg = _conf_single_cell()
        cfg.simulations = {
            "test": {
                "simulator": "nest",
                "duration": duration,
                "resolution": resolution,
                "seed": 1234,
                "cell_models": {
                    "A": {
                        "model": "iaf_cond_alpha",
                        "constants": {
                            "V_reset": -70,  # V_m, E_L and V_reset are the same
                        },
                    }
                },
                "connection_models": {},
                "devices": {
                    "dict_spike_gen": {
                        "device": "sinusoidal_poisson_generator",
                        "delay": resolution,
                        "weight": 1.0,
                        "rate": 1000.0,
                        "amplitude": 1000,
                        "frequency": 20,
                        "start": 10.0,
                        "stop": 10.0,
                        "phase": 2,
                        "targetting": {
                            "strategy": "cell_model",
                            "cell_models": ["A"],
                        },
                    }
                },
            }
        }
        with self.assertRaises(ConfigurationError):
            Scaffold(cfg, self.storage)

    def test_multisyn(self):
        duration = 100
        resolution = 0.1
        cfg = _conf_single_cell()
        cfg.cell_types.add("C", {"spatial": {"radius": 1, "count": 1}})
        cfg.placement.add(
            "placement_C",
            {
                "strategy": "bsb.placement.strategy.FixedPositions",
                "cell_types": ["C"],
                "partitions": ["B"],
                "positions": [[0, 0, 0]],
            },
        )
        cfg.connectivity.add(
            "C_to_A",
            {
                "strategy": "bsb.connectivity.AllToAll",
                "presynaptic": {"cell_types": ["C"]},
                "postsynaptic": {"cell_types": ["A"]},
            },
        )
        cfg.simulations = {
            "test": {
                "simulator": "nest",
                "duration": duration,
                "resolution": resolution,
                "seed": 1234,
                "cell_models": {
                    "A": {
                        "model": "iaf_cond_alpha",
                        "constants": {
                            "V_reset": -70,  # V_m, E_L and V_reset are the same
                        },
                    },
                    "C": {"model": "parrot_neuron"},
                },
                "connection_models": {
                    "C_to_A": {
                        "synapses": [
                            {"weight": -20.25, "delay": 1},
                            {"weight": -60.25, "delay": 30},
                        ],
                    }
                },
                "devices": {
                    "pg": {
                        "device": "poisson_generator",
                        "rate": 10.0,  # should produce one spike
                        "targetting": {
                            "strategy": "cell_model",
                            "cell_models": ["C"],
                        },
                        "weight": 20.0,
                        "delay": resolution,
                    },
                    "record_C_spikes": {
                        "device": "spike_recorder",
                        "delay": resolution,
                        "targetting": {
                            "strategy": "cell_model",
                            "cell_models": ["C"],
                        },
                    },
                    "voltmeter_A": {
                        "device": "multimeter",
                        "delay": resolution,
                        "properties": ["V_m"],
                        "units": ["mV"],
                        "targetting": {
                            "strategy": "cell_model",
                            "cell_models": ["A"],
                        },
                    },
                },
            }
        }
        netw = Scaffold(cfg, self.storage)
        netw.compile()
        results = netw.run_simulation("test")

        # get spike time of first spike of C
        spike_times_bsb = results.spiketrains[1]
        self.assertEqual("record_C_spikes", spike_times_bsb.annotations["device"])
        membrane_potentials = results.analogsignals[0].magnitude[:, 0]
        time_effect_first_syn = int((spike_times_bsb.magnitude[0] + 1) / resolution)
        time_effect_sec_syn = int((spike_times_bsb.magnitude[0] + 30) / resolution)
        self.assertClose(membrane_potentials[time_effect_first_syn - 1], -70.0, atol=1e-5)
        # both synapses of A have an inhibitory effect. They are separated by 2 ms
        # Check impact of the first synapse
        self.assertLess(membrane_potentials[time_effect_first_syn], -70.0)
        # second synapse arrives after the peak of the postsynaptic receptor,
        # so its effect should hyperpolarize A's membrane potential
        # Check impact of the second synapse
        self.assertLess(
            membrane_potentials[time_effect_sec_syn - 2],
            membrane_potentials[time_effect_sec_syn - 1],
        )
        self.assertLess(
            membrane_potentials[time_effect_sec_syn],
            membrane_potentials[time_effect_sec_syn - 1],
        )

    def test_unknown_synapse(self):
        duration = 100
        resolution = 0.1
        cfg = _conf_two_cells()
        with self.assertRaises(CastError):
            cfg.simulations = {
                "test": {
                    "simulator": "nest",
                    "duration": duration,
                    "resolution": resolution,
                    "seed": 1234,
                    "cell_models": {
                        "A": {"model": "iaf_cond_alpha"},
                        "C": {"model": "parrot_neuron"},
                    },
                    "connection_models": {
                        "C_to_A": {
                            "synapses": [
                                {"model": "blabla", "weight": -20.25, "delay": 1},
                            ],
                        }
                    },
                    "devices": {},
                }
            }

    def test_gap_junctions_syn(self):
        duration = 100
        resolution = 0.1
        cfg = _conf_two_cells()
        cfg.simulations = {
            "test": {
                "simulator": "nest",
                "duration": duration,
                "resolution": resolution,
                "seed": 1234,
                "cell_models": {
                    "A": {"model": "hh_psc_alpha_gap"},
                    "C": {"model": "hh_psc_alpha_gap"},
                },
                "connection_models": {
                    "C_to_A": {
                        "synapses": [
                            {"model": "gap_junction", "weight": -20.25},
                        ],
                    }
                },
                "devices": {},
            }
        }
        scaffold = Scaffold(cfg, self.storage)
        scaffold.compile()
        scaffold.run_simulation("test")

    def test_error_gap_junctions_syn(self):
        duration = 100
        resolution = 0.1
        cfg = _conf_two_cells()
        with self.assertRaises(ConfigurationError):
            cfg.simulations = {
                "test": {
                    "simulator": "nest",
                    "duration": duration,
                    "resolution": resolution,
                    "seed": 1234,
                    "cell_models": {
                        "A": {"model": "hh_psc_alpha_gap"},
                        "C": {"model": "hh_psc_alpha_gap"},
                    },
                    "connection_models": {
                        "C_to_A": {
                            "synapses": [
                                {"weight": -20.25},
                            ],
                        }
                    },
                    "devices": {},
                }
            }

    def test_multisyn_collocation(self):
        cfg = _conf_single_cell()
        cfg.cell_types.add("C", {"spatial": {"radius": 1, "count": 30}})
        cfg.placement.add(
            "placement_C",
            {
                "strategy": "bsb.placement.RandomPlacement",
                "cell_types": ["C"],
                "partitions": ["B"],
            },
        )
        cfg.connectivity.add(
            "C_to_A",
            {
                "strategy": "bsb.connectivity.AllToAll",
                "presynaptic": {"cell_types": ["C"]},
                "postsynaptic": {"cell_types": ["A"]},
            },
        )
        cfg.simulations = {
            "test": {
                "simulator": "nest",
                "duration": 100,
                "resolution": 0.1,
                "seed": 1234,
                "cell_models": {
                    "A": {
                        "model": "iaf_cond_alpha",
                        "constants": {
                            "V_reset": -70,  # V_m, E_L and V_reset are the same
                        },
                    },
                    "C": {"model": "parrot_neuron"},
                },
                "connection_models": {
                    "C_to_A": {
                        "rule": "pairwise_bernoulli",  # random connection rule
                        "p": 0.6,
                        "synapses": [
                            {"weight": 30, "delay": 1.0, "model": "static_synapse"},
                            {"weight": 30, "delay": 1.0, "model": "stdp_synapse"},
                        ],
                    }
                },
                "devices": {},
            }
        }
        scaffold = Scaffold(cfg, self.storage)
        scaffold.compile()
        adapter = NestAdapter()
        adapter.reset_kernel()
        adapter.prepare(scaffold.simulations["test"])
        conn_data = np.array(
            [
                (
                    conn.source,
                    conn.target,
                    1
                    if conn.synapse_model == "static_synapse"
                    else 2
                    if conn.synapse_model == "stdp_synapse"
                    else 0,
                )
                for conn in nest.GetConnections()
            ]
        )
        u, c = np.unique(conn_data[:, 2], return_counts=True)
        self.assertAll(np.array([1, 2]) == u, "synapses should be either static or stdp")
        self.assertEqual(
            c[0], c[1], "there should be as many static and stdp connections"
        )
        self.assertAll(
            conn_data[:, :2][conn_data[:, 2] == 1]
            == conn_data[:, :2][conn_data[:, 2] == 2],
            "the cell pairs should be the same for static and stdp synapses",
        )
