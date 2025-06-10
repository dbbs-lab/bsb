import unittest

import _shared

from patch import p
from patch.exceptions import BroadcastError, ParallelConnectError


@unittest.skipIf(
    p.parallel.nhost() != 1, "Single host tests should run only on 1 MPI node."
)
class TestSingleHostParallel(_shared.NeuronTestCase):
    """
    Test parallel network approach functioning on a single MPI node.
    """

    def test_pc_singleton(self):
        pc = p.parallel
        pc2 = p.parallel
        self.assertEqual(pc, pc2)
        self.assertEqual(pc.id(), 0)

    def test_parallel_con(self):
        s = p.Section()
        s.push()
        p.ParallelCon(s, 202020)
        p.pop_section()
        syn = p.Section().synapse(p.ExpSyn)
        p.ParallelCon(1, syn, 5, 1)
        with self.assertRaises(ParallelConnectError):
            p.ParallelCon(None, None)

    def test_parallel_con_props(self):
        s = p.Section()
        pc = p.ParallelCon(s, 202021, delay=5, weight=3)
        self.assertEqual(5, pc.delay, "Delay not set")
        self.assertEqual(3, pc.weight[0], "Weight not set")

    def test_parallel_context(self):
        pc1 = p.ParallelContext()
        pc2 = p.parallel
        self.assertEqual(pc1.nhost(), pc2.nhost(), "nhost mismatch")

    def test_single_bcast(self):
        arr = p.parallel.broadcast([1, 2, 3])
        self.assertEqual([1, 2, 3], arr, "single node broadcast failed")
        v = p.parallel.broadcast(p.Vector([1, 2, 3]))
        self.assertEqual([1, 2, 3], list(v), "single node vector broadcast failed")
        with self.assertRaises(BroadcastError):
            p.parallel.broadcast(p.NetStim())


@unittest.skipIf(
    p.parallel.nhost() == 1, "Cannot test parallel networks on a single MPI node."
)
class TestParallelNetworks(_shared.NeuronTestCase):
    """
    Test true functioning of parallel networks on multiple MPI nodes.
    """

    def test_parallel_prop(self):
        self.assertEqual(p.parallel, p.ParallelContext(), "PC should be a singleton")

    def test_broadcasting(self):
        # Try sending a string
        x = p.parallel.broadcast("Arbitrary")
        self.assertEqual(
            x,
            "Arbitrary",
            msg=f"Arbitrary data mangled on node {p.parallel.id()}",
        )

        class Local:
            pass

        self.assertRaises(BroadcastError, p.parallel.broadcast, Local())
        # Try sending from a different node
        x = 5 if p.parallel.id() == 0 else 12
        y = p.parallel.broadcast(x, root=1)
        self.assertEqual(y, 12, msg="Node specification ignored in broadcast.")
        self.assertRaises(BroadcastError, p.parallel.broadcast, p.NetStim())
        self.assertRaises(BroadcastError, p.parallel.broadcast, p.Section())


class TestParallelPointProcess(_shared.NeuronTestCase):
    def _setup_synapse_parallel(self):
        section = p.Section()
        syn = section.synapse(p.ExpSyn, attributes={"tau": 2})
        if not p.parallel.id():
            syn.stimulate(start=0, number=5, interval=10, delay=1, weight=0.04)
            p.ParallelCon(section, 3030, threshold=-52, delay=1)
        else:
            p.ParallelCon(3030, syn, weight=0.04)
        return p.time, section.record()

    def _setup_synapse_patch(self):
        section = p.Section()
        syn = section.synapse(p.ExpSyn, attributes={"tau": 2})
        syn.stimulate(start=0, number=5, interval=10, delay=1, weight=0.04)
        section2 = p.Section()
        syn_r = section2.synapse(p.ExpSyn, attributes={"tau": 2})
        section.connect_synapse(syn_r, delay=1, weight=0.04, threshold=-52)

        return p.time, section2.record()

    # noinspection DuplicatedCode
    def _setup_synapse_neuron(self):
        from neuron import h

        pc = h.ParallelContext()
        if not pc.id():
            my_s = h.Section()
            syn_ = h.ExpSyn(my_s(0.5))
            syn_.tau = 2
            stim = h.NetStim()
            stim.number = 5
            stim.start = 0
            stim.interval = 10
            ncstim = h.NetCon(stim, syn_)
            ncstim.weight[0] = 0.04
            ncstim.delay = 1
            nc_emit = h.NetCon(my_s(0.5)._ref_v, None, sec=my_s)
            nc_emit.threshold = -52
            nc_emit.delay = 1
            pc.set_gid2node(3031, pc.id())
            pc.cell(3031, nc_emit)
            pc.outputcell(3031)
            self._store = [my_s, stim, syn_, ncstim, nc_emit]
        else:
            my_s = h.Section()
            syn_ = h.ExpSyn(my_s(0.5))
            syn_.tau = 2
            nc_recv = pc.gid_connect(3031, syn_)
            nc_recv.weight[0] = 0.04
            self._store = [my_s, syn_, nc_recv]

        return h.Vector().record(h._ref_t), h.Vector().record(my_s(0.5)._ref_v)

    def test_synapse(self):
        """
        Tests whether spikes get transferred across nodes.
        """
        tpp, vpp = self._setup_synapse_parallel()
        tps, vps = self._setup_synapse_patch()
        tn, vn = self._setup_synapse_neuron()

        p.finitialize()
        p.parallel.psolve(100)

        if p.parallel.id():
            self.assertNotEqual(min(*vpp), max(*vpp), "No Vm diff observed")
            self.assertEqual(
                [*tpp], [*tn], "Time vector differences in synaptic comparison"
            )
            self.assertEqual([*vpp], [*vn], "Outcome differences in synaptic comparison")
            self.assertEqual(
                [*tpp], [*tps], "Time vector differences in serial/parallel comparison"
            )
            self.assertEqual(
                [*vpp], [*vps], "Outcome differences in serial/parallel comparison"
            )

    # noinspection DuplicatedCode
    def _setup_neuron_across_nodes(self):
        from neuron import h

        pc = h.ParallelContext()
        if not pc.id():
            my_s = h.Section()
            syn_ = h.ExpSyn(my_s(0.5))
            syn_.tau = 2
            stim = h.NetStim()
            stim.number = 5
            stim.start = 0
            stim.interval = 10
            ncstim = h.NetCon(stim, syn_)
            ncstim.weight[0] = 0.04
            ncstim.delay = 1
            nc_emit = h.NetCon(my_s(0.5)._ref_v, None, sec=my_s)
            nc_emit.threshold = -52
            nc_emit.delay = 1
            pc.set_gid2node(3032, pc.id())
            pc.cell(3032, nc_emit)
            pc.outputcell(3032)
            self._store3 = [my_s, stim, syn_, ncstim, nc_emit]

        my_s2 = h.Section()
        syn_2 = h.ExpSyn(my_s2(0.5))
        syn_2.tau = 2
        nc_recv = pc.gid_connect(3032, syn_2)
        nc_recv.weight[0] = 0.04
        self._store4 = [my_s2, syn_2, nc_recv]
        return h.Vector().record(h._ref_t), h.Vector().record(my_s2(0.5)._ref_v)

    # noinspection DuplicatedCode
    def _setup_patch_across_nodes(self):
        from patch import p

        pc = p.parallel
        if not pc.id():
            my_s = p.Section()
            syn_ = my_s.synapse(p.ExpSyn, attributes={"tau": 2})
            syn_.stimulate(number=5, start=0, interval=10, weight=0.04, delay=1)
            p.ParallelCon(my_s, 3033, threshold=-52, delay=1)

        my_s2 = p.Section()
        syn_2 = my_s2.synapse(p.ExpSyn, attributes={"tau": 2})
        nc_recv = p.ParallelCon(3033, syn_2)
        # Assert https://github.com/neuronsimulator/nrn/issues/2135
        with self.assertRaises(RuntimeError):
            nc_recv.threshold = -20
        nc_recv.weight[0] = 0.04
        return p.time, p.record(my_s2(0.5)._ref_v)

    def test_same_node_synapse(self):
        """
        Tests whether spikes get transferred across nodes.
        """
        tps, vps = self._setup_patch_across_nodes()
        tpn, vpn = self._setup_neuron_across_nodes()
        import numpy as np

        from patch import p

        spt, spid = p.parallel.spike_record()
        p.parallel._warn_new_gids = False

        p.run(100)

        spikes = [3032, 3033] if not p.parallel.id() else []
        self.assertEqual(len(spikes), len(spid), "expected 2 on main, 0 elsewhere")
        self.assertEqual(spikes, sorted(list(spid)), "expected 2 on main, 0 elsewhere")
        arr = np.array(p.parallel.py_allgather(list(vps)))
        self.assertGreater(arr.shape[1], 0, "No signal recorded")
        self.assertTrue(np.allclose(np.diff(arr, axis=0), 0), "Diff output on diff nodes")
        ar2 = np.array(p.parallel.py_allgather(list(vpn)))
        self.assertGreater(ar2.shape[1], 0, "No signal recorded")
        self.assertTrue(np.allclose(np.diff(ar2, axis=0), 0), "Diff output on diff nodes")
        self.assertTrue(np.allclose(arr, ar2), "NEURON vs Patch differences")
