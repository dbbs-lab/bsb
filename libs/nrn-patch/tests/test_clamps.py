import _shared

from patch import p


class TestClamps(_shared.NeuronTestCase):
    """
    Test the current and voltage clamp mechanisms
    """

    def setUp(self):
        pass

    def test_iclamp(self):
        s0 = p.Section()
        s0.record()
        s1 = p.Section()
        s1.record()
        s2 = p.Section()
        s2.record()
        s3 = p.Section()
        s3.record()
        s4 = p.Section()
        s4.record()
        p.time

        cs = s1.iclamp(amplitude=10, delay=5)
        c = p.IClamp(sec=s2)
        c.amp = 10
        c.dur = 10
        c2 = s3.iclamp(amplitude=10)
        s4.iclamp(amplitude=[-10 for _ in range(int(10 / p.dt))])

        self.assertEqual(10, cs.amplitude, "fcall setter mismatch")
        self.assertEqual(10, c.amplitude, "direct neuron setter mismatch")
        self.assertEqual(10, cs.__neuron__().amp, "clamp amp setting failed")

        p.finitialize()
        p.continuerun(10)

        self.assertGreater(
            max(s1.recordings[0.5]),
            max(s0.recordings[0.5]),
            "No injected current detected",
        )
        self.assertGreater(
            max(s2.recordings[0.5]),
            max(s0.recordings[0.5]),
            "No injected current detected",
        )
        self.assertGreater(
            max(s3.recordings[0.5]),
            max(s0.recordings[0.5]),
            "No injected current detected",
        )
        self.assertGreater(
            max(s3.recordings[0.5]),
            max(s1.recordings[0.5]),
            "Half of injected charge not smaller than full charge",
        )
        self.assertGreater(
            min(s0.recordings[0.5]),
            min(s4.recordings[0.5]),
            "No negative injected current detected",
        )

    def test_seclamp(self):
        clamp = p.SEClamp(p.Section())
        self.assertEqual(100, clamp.delay, "default delay should be 100")
        clamp.delay = 102
        self.assertEqual(102, clamp.__neuron__().dur1, "delay setting failed")
        self.assertEqual(102, clamp.delay, "delay get failed")
        clamp.duration = 102
        self.assertEqual(102, clamp.__neuron__().dur2, "duration setting failed")
        self.assertEqual(102, clamp.duration, "duration get failed")
        clamp.after = 102
        self.assertEqual(102, clamp.__neuron__().dur3, "after setting failed")
        self.assertEqual(102, clamp.after, "duration get failed")
