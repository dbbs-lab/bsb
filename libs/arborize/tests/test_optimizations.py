import pathlib
import unittest

from arborize import bluepyopt_build, define_constraints, file_schematic


class TestBluePyOptimization(unittest.TestCase):
    def test_hh_pas(self):
        import bluepyopt
        from bluepyopt import ephys

        constraints = define_constraints(
            {
                "cable_types": {
                    "soma": {
                        "cable": {"Ra": 100.0, "cm": 1.0},
                        "ions": {},
                        "mechanisms": {
                            "hh": {
                                "gnabar": [0.05, 0.125],
                                "gkbar": [0.01, 0.075],
                            },
                        },
                    },
                },
            }
        )
        schema = file_schematic(
            pathlib.Path(__file__).parent / "data" / "morphologies" / "simple.swc",
            definitions=constraints,
        )
        cell_model = bluepyopt_build(schema)
        self.assertEquals(["soma"], cell_model.seclist_names)

        self.assertEquals(1, len(cell_model.mechanisms))
        self.assertEquals("hh", cell_model.mechanisms[0].name)
        self.assertEquals("hh", cell_model.mechanisms[0].prefix)
        self.assertEquals(1, len(cell_model.mechanisms[0].locations))
        self.assertEquals("soma", cell_model.mechanisms[0].locations[0].seclist_name)
        self.assertEquals(5, len(cell_model.params))

        soma_loc = ephys.locations.NrnSeclistCompLocation(
            name="soma", seclist_name="soma", sec_index=0, comp_x=0.5
        )
        nrn = ephys.simulators.NrnSimulator()

        sweep_protocols = []
        for protocol_name, amplitude in [("step1", 0.01), ("step2", 0.05)]:
            stim = ephys.stimuli.NrnSquarePulse(
                step_amplitude=amplitude,
                step_delay=100,
                step_duration=50,
                location=soma_loc,
                total_duration=200,
            )
            rec = ephys.recordings.CompRecording(
                name="%s.soma.v" % protocol_name, location=soma_loc, variable="v"
            )
            protocol = ephys.protocols.SweepProtocol(protocol_name, [stim], [rec])
            sweep_protocols.append(protocol)
        twostep_protocol = ephys.protocols.SequenceProtocol(
            "twostep", protocols=sweep_protocols
        )

        efel_feature_means = {"step1": {"Spikecount": 1}, "step2": {"Spikecount": 5}}

        objectives = []

        for protocol in sweep_protocols:
            stim_start = protocol.stimuli[0].step_delay
            stim_end = stim_start + protocol.stimuli[0].step_duration
            for efel_feature_name, mean in efel_feature_means[protocol.name].items():
                feature_name = "%s.%s" % (protocol.name, efel_feature_name)
                feature = ephys.efeatures.eFELFeature(
                    feature_name,
                    efel_feature_name=efel_feature_name,
                    recording_names={"": "%s.soma.v" % protocol.name},
                    stim_start=stim_start,
                    stim_end=stim_end,
                    exp_mean=mean,
                    exp_std=0.05 * mean,
                )
                objective = ephys.objectives.SingletonObjective(feature_name, feature)
                objectives.append(objective)

        score_calc = ephys.objectivescalculators.ObjectivesCalculator(objectives)
        cell_evaluator = ephys.evaluators.CellEvaluator(
            cell_model=cell_model,
            param_names=["gnabar_hh_soma", "gkbar_hh_soma"],
            fitness_protocols={twostep_protocol.name: twostep_protocol},
            fitness_calculator=score_calc,
            sim=nrn,
        )

        optimisation = bluepyopt.optimisations.DEAPOptimisation(
            evaluator=cell_evaluator, offspring_size=10
        )
        final_pop, hall_of_fame, logs, hist = optimisation.run(max_ngen=5)

        best_ind = hall_of_fame[0]
        best_ind_dict = cell_evaluator.param_dict(best_ind)
        outcome = cell_evaluator.evaluate_with_dicts(best_ind_dict)
        self.assertAlmostEqual(0.12, best_ind_dict["gnabar_hh_soma"], 2)
        self.assertAlmostEqual(0.011, best_ind_dict["gkbar_hh_soma"], 3)
        self.assertGreater(outcome["step2.Spikecount"], outcome["step1.Spikecount"])
