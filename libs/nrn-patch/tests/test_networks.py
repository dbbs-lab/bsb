from random import random

import _shared

from patch import NotConnectableError, NotConnectedError, connection, p
from patch.objects import NetCon


class TestNetworks(_shared.NeuronTestCase):
    """
    Test network use cases such as PointProcesses, NetCon, NetStim, VecStim, ...
    """

    def test_connection_helper(self):
        s = p.Section()
        pp = p.ExpSyn(s)
        stim = pp.stimulate()
        self.assertEqual(
            NetCon,
            type(connection(stim, pp)),
            "connection helper did not return the expected NetCon",
        )
        self.assertRaises(NotConnectedError, connection, s, s)
        self.assertRaises(NotConnectableError, connection, p.Vector(), s)
        self.assertRaises(NotConnectableError, connection, s, p.Vector())

    def test_stimulate(self):
        s1 = p.Section()
        s2 = p.Section()
        s3 = p.Section()
        se = p.ExpSyn(s1)
        se2 = p.ExpSyn(s2)
        se3 = p.ExpSyn(s3)
        ns = se.stimulate(start=1, number=3, interval=1)
        vs = se2.stimulate(pattern=[1, 2, 3])
        vs2 = se3.stimulate(pattern=[random() * 2, random() + 2, random() * 2 + 3])
        rs1 = s1.record()
        rs2 = s2.record()
        rs3 = s3.record()
        t = p.time

        p.finitialize()
        p.continuerun(10)
        self.assertGreater(
            max(list(rs1)), min(list(rs1)), "Flatline where stimulation was expected."
        )
        for ns_y, vs_y in zip(rs1, rs2):
            self.assertAlmostEqual(ns_y, vs_y, delta=1e-6)
        equal = True
        for vs_y, vs2_y in zip(rs2, rs3):
            equal = abs(vs2_y - vs_y) < 1e-6
            if not equal:
                break
        equal = False
        self.assertFalse(equal, "Random and periodic VecStim yielded identical results.")

    def test_netcon_record(self):
        s1 = p.Section()
        se = p.ExpSyn(s1)
        ns = se.stimulate(start=1, number=3, interval=1, weight=100)
        r = s1.record()
        s2 = p.Section()
        r2 = s2.record()
        syn = p.ExpSyn(s2)
        nc = s1.connect_synapse(syn)
        v = p.Vector()
        t = p.time
        nc.record(v)
        v2 = nc.record()
        v3 = nc.record()

        p.finitialize()
        p.continuerun(10)

        self.assertEqual(v, v2, "NetCon recorder should be a singleton.")
        self.assertEqual(v2, v3, "NetCon recorder should be a singleton.")
        self.assertNotEqual(len(v), 0, "NetCon recorder should record a spike.")
        self.assertEqual(
            len(v), len(v2), "Different NetCon recorders should record same spikes."
        )
