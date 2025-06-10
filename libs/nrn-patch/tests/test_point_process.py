import _shared

import patch.objects
from patch import p


class TestPointProcess(_shared.NeuronTestCase):
    def _setup_synapse_patch(self):
        section = p.Section()
        syn = section.synapse(p.ExpSyn, attributes={"tau": 2})
        syn.stimulate(start=0, number=5, interval=10, delay=1, weight=0.04)

        return p.time, section.record()

    def _setup_synapse_neuron(self):
        from neuron import h

        my_s = h.Section()
        syn_ = h.ExpSyn(my_s(0.5))
        syn_.tau = 2
        stim = h.NetStim()
        stim.number = 5
        stim.start = 0
        stim.interval = 10
        ncstim = h.NetCon(stim, syn_)
        ncstim.delay = 1
        soma_v = h.Vector().record(my_s(0.5)._ref_v)
        t = h.Vector().record(h._ref_t)
        ncstim.weight[0] = 0.04

        self._store = [my_s, stim, syn_, ncstim]
        return t, soma_v

    def test_synapse(self):
        tp, vp = self._setup_synapse_patch()
        tn, vn = self._setup_synapse_neuron()

        p.run(30)

        self.assertEqual([*tp], [*tn], "Time vector differences in synaptic comparison")
        self.assertEqual([*vp], [*vn], "Outcome differences in synaptic comparison")

    def test_wrapper(self):
        section = p.Section()
        syn = section.synapse(p.ExpSyn)
        self.assertIs(
            patch.objects.PointerWrapper, type(type(syn).e), "ExpSyn pointer not wrapped"
        )
        self.assertEqual(0, syn.e, "Wrapper get incorrect")
        syn.e = 4
        self.assertEqual(4, syn.__neuron__().e, "Wrapper set failed")
        self.assertIs(
            patch.objects.PointerWrapper, type(type(syn).e), "Wrapper set broke wrapper"
        )
