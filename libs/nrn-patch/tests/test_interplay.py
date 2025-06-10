import _shared

import patch
from patch import NotConnectableError, p


class TestInterplay(_shared.NeuronTestCase):
    """
    Test whether mixing h and p together causes issues.
    """

    def setUp(self):
        pass

    def test_section_connect(self):
        from neuron import h

        # Connect 2 Sections
        s = p.Section()
        s2 = p.Section()
        s.connect(s2)

        # Connect a Section to a neuron Section
        s = p.Section()
        nrn_s = h.Section()
        nrn_s.connect(s.__neuron__())

        # Connect a neuron section to a section
        s = p.Section()
        nrn_s = h.Section()
        s.connect(nrn_s)

    def test_netcon_inter(self):
        from neuron import h

        s1 = h.NetStim()
        s2 = h.NetStim()
        s3 = p.NetStim()
        s4 = p.NetStim()
        # Test that only Python objects that play by the rules can be connected.
        self.assertRaises(NotConnectableError, p.NetCon, s1, s2)
        self.assertRaises(NotConnectableError, p.NetCon, s3, s2)
        self.assertRaises(NotConnectableError, p.NetCon, s1, s4)
        self.assertEqual(
            patch.objects.NetCon, type(p.NetCon(s3, s4)), "Valid NetCon failed"
        )
