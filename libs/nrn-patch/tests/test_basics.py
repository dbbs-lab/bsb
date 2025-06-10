import unittest

import _shared

import patch.objects
from patch import is_density_mechanism, is_point_process, p
from patch.exceptions import HocRecordError
from patch.version import get_neuron_version


class TestPatchRegistration(_shared.NeuronTestCase):
    """
    Check that the registration of PythonHocObjects works.

    (Will almost never be relevant
    since most actual HocObjects will be covered by Patch and use the registration queue
    rather than immediate registration; and any class names that don't correspond to an
    actual ``h.<name>`` function don't create a wrapper)
    """

    def test_registration(self):
        # Create a new PythonHocObject, no wrapper will be added as it does not exist in h
        class NewHocObject(patch.objects.PythonHocObject):
            pass

        # Nothing to test, but the import inside ``PythonHocObject.__init_subclass__``
        # should complete and the call to ``PythonHocInterpreter.register_hoc_object``
        # should be covered in test coverage results.


class TestSimulationControl(_shared.NeuronTestCase):
    def test_continuerun(self):
        p.finitialize(-70)
        p.continuerun(10)
        p.continuerun(10)
        self.assertAlmostEqual(20, p.t)

    def test_run(self):
        p.finitialize(-70)
        p.run(10)
        self.assertAlmostEqual(10, p.t)


@unittest.skipIf(
    p.parallel.nhost() != 1, "Avoid NEURON throwing MPI_ABORTs for weird tests"
)
class TestPatch(_shared.NeuronTestCase):
    """
    Check Patch basics like object wrapping and the standard interface.
    """

    def setUp(self):
        pass

    def test_attributes(self):
        # Test Hoc attributes
        self.assertTrue(p.E - 2.7 < 0.2, "Can't read attributes from HocInterpreter")
        p.celsius = 11.004
        self.assertEqual(
            p._PythonHocInterpreter__h.celsius,
            11.004,
            "Can't set attributes on HocInterpreter",
        )
        # Test python hoc attributes
        p.something_else = 15.4
        self.assertEqual(
            p.__dict__["something_else"],
            15.4,
            "Can't set attributes on PythonHocInterpreter",
        )
        # Test nonsense attributes
        self.assertRaises(AttributeError, lambda: p.doesnt_exist)
        # Test object attributes
        s = p.Section()
        s.nseg = 5
        self.assertEqual(s.__neuron__().nseg, 5, "Couldn't set attributes on HocObject")
        s.nseggg = 55
        self.assertRaises(AttributeError, lambda: s.__neuron__().nseggg)
        self.assertEqual(
            s.__dict__["nseggg"], 55, "Couldn't set attributes on PythonHocObject"
        )

    def test_wrapping(self):
        net_con = type(p.NetCon(p.NetStim(), p.NetStim()))
        net_stim = type(p.NetStim())
        section = type(p.Section())
        self.assertEqual(
            section,
            patch.objects.Section,
            "Incorrect Section wrapping: " + str(section),
        )
        self.assertEqual(
            net_stim,
            patch.objects.NetStim,
            "Incorrect NetStim wrapping: " + str(net_stim),
        )
        self.assertEqual(
            net_con, patch.objects.NetCon, "Incorrect NetCon wrapping: " + str(net_con)
        )

    def test_transform(self):
        from patch import transform, transform_arc, transform_netcon, transform_record

        nrn_section1 = transform(p.Section())
        self.assertEqual(
            "nrn",
            type(nrn_section1).__module__,
            "Transform on a Patch object did not return a NEURON object.",
        )
        self.assertIs(
            nrn_section1,
            transform(nrn_section1),
            "Transform on a NEURON object did not return the object.",
        )
        seg = p.Section()(0.5)
        nv = get_neuron_version()
        self.assertIn(
            "pointer to hoc scalar" if nv < "9.0a0" else "data_handle<",
            str(transform_record(seg)),
            "Recording transform on a Segment did not return a pointer to a scalar.",
        )
        self.assertIn(
            "pointer to hoc scalar" if nv < "9.0a0" else "data_handle<",
            str(transform_netcon(seg)),
            "NetCon transform on a Segment did not return a pointer to a scalar.",
        )
        self.assertIn(
            "pointer to hoc scalar" if nv < "9.0a0" else "data_handle<",
            str(transform_netcon(p.Section())),
            "NetCon transform on a Section did not return a pointer to a scalar.",
        )
        section = p.Section()
        self.assertEqual(
            transform(section(0.5)),
            transform_arc(section),
            "Default arc transform did not yield default segment",
        )
        self.assertEqual(
            transform(section(0.5)),
            transform_arc(section),
            "Default arc transform did not yield default segment",
        )
        self.assertEqual(
            transform(1),
            transform_arc(1),
            "Transform arc on non-arced object should yield transform of the object",
        )

    def test_is_point_process(self):
        from neuron import h

        pps = [s for s in dir(h) if is_point_process(s)]
        pp_attrs = []
        for s in dir(h):
            try:
                attr = getattr(h, s)
            except Exception:
                pass
            else:
                if is_point_process(attr):
                    pp_attrs.append(s)
        self.assertEqual(
            [
                "APCount",
                "AlphaSynapse",
                "Exp2Syn",
                "ExpSyn",
                "IClamp",
                "OClamp",
                "PointProcessMark",
                "SEClamp",
                "VClamp",
            ],
            pps,
            "Diff point processes",
        )
        self.assertEqual(pps, pp_attrs, "Diff when using `is_point_process` with attrs")

    def test_is_density_mechanism(self):
        from neuron import h

        dms = [s for s in dir(h) if is_density_mechanism(s)]
        self.assertEqual(
            [
                "extracellular",
                "fastpas",
                "hh",
                "k_ion",
                "na_ion",
                "pas",
            ],
            dms,
            "Diff density mechanisms",
        )
        s = h.Section()
        s.insert("pas")
        self.assertTrue(is_density_mechanism(s(0.5).pas), "Density mech not detected")

    def test_record(self):
        s = p.Section()
        v = p.record(s)
        self.assertEqual(patch.objects.Vector, type(v), "p.record should return Vector")
        sr = p.SectionRef(s)
        with self.assertRaises(HocRecordError):
            v = p.record(sr)
        with self.assertRaises(HocRecordError):
            v = p.record(4)


class TestSection(_shared.NeuronTestCase):
    def test_section_call(self):
        s = p.Section()
        s.nseg = 5
        seg = s(0.5)
        self.assertEqual(
            patch.objects.Segment, type(seg), "Section call did not return a Segment"
        )
        self.assertEqual(
            "<class 'nrn.Segment'>",
            str(type(seg.__neuron__())),
            "Section call did not return a NEURON Segment pointer",
        )

    def test_section_attr(self):
        transform = patch.transform
        s = p.Section()
        s.set_dimensions(10, 10)
        self.assertEqual(s.L, 10, "Dimension setter failed.")
        self.assertEqual(s.diam, 10, "Dimension setter failed.")
        s.add_3d([[0.0, 0.0, 0.0]])
        self.assertEqual(
            (s.x3d(0), s.y3d(0), s.z3d(0), s.diam3d(0)),
            (0.0, 0.0, 0.0, 10.0),
            "Add 3D no diam spec failed",
        )
        s.pt3dclear()
        s.add_3d([[0.0, 2.0, 0.0], [4.0, 3.0, 2.0]], 4)
        self.assertEqual(
            (s.x3d(0), s.y3d(0), s.z3d(1), s.diam3d(0)),
            (0.0, 2.0, 2.0, 4.0),
            "Add 3D diam spec failed",
        )
        s.connect(p.Section())
        s.connect(p.Section())
        s.connect(p.Section())
        self.assertEqual(
            list(map(transform, s.wholetree())),
            transform(s).wholetree(),
            "Wholetree diff",
        )

    def test_record_access(self):
        s = p.Section()
        r = s.record(0.5)
        r2 = s.record(0.7)
        self.assertNotEqual(r, r2, "Recorders at 0.5 and 0.7 should not be equal")
        self.assertEqual(r, s.record(0.5), "Recorders at 0.5 should be equal")

    def test_section_iter(self):
        s = p.Section()
        s.nseg = 5
        count = 0
        for seg in s:
            count += 1
            self.assertEqual(
                patch.objects.Segment,
                type(seg),
                "Section iteration did not return a Segment",
            )
        self.assertEqual(count, 5, "Section iteration did not return `nseg` segments.")
        # Test that other HocObjects aren't iterable.
        self.assertRaises(TypeError, iter, p.NetStim())

    def test_section_cas_push_pop(self):
        s = p.Section()
        s2 = p.Section()
        s.push()
        self.assertEqual(s, p.cas(), "Push should put section on stack")
        with s2.push():
            self.assertEqual(s2, p.cas(), "Context push should put section on stack")
        self.assertEqual(s, p.cas(), "Context exit should remove section from stack")
        self.assertRaises(RuntimeError, s2.pop)
        # Cleanup stack after test
        s.pop()

    def test_section_synapse_insertion(self):
        s = p.Section()
        s.synapse(p.ExpSyn)
        self.assertEqual(
            1, len(s._references), "Section.synapse call should store product."
        )
        self.assertEqual(
            1,
            len(s._references[0]._references),
            "Section.synapse call should store reciprocal reference on product.",
        )
        self.assertEqual(
            s,
            s._references[0]._references[0],
            "Section.synapse call should store reciprocal reference on product.",
        )
        self.assertFalse(
            hasattr(s, "synapses"),
            "Synapse should not be stored on section unless explicitly specified.",
        )
        syn = s.synapse(p.ExpSyn, store=True)
        self.assertTrue(
            hasattr(s, "synapses"),
            "Synapse should have been stored on section as it was explicitly specified.",
        )
        self.assertIn(syn, s.synapses, "Synapse product not found in synapse collection.")


class TestSectionRef(_shared.NeuronTestCase):
    def test_ref(self):
        s = p.Section()
        s2 = p.Section()
        s.connect(s2)
        s2.connect(s)
        sr = p.SectionRef(s)
        _sr2 = p.SectionRef(sec=s2)
        self.assertIs(sr.section, s, "SectionRef section stored incorrectly.")
        self.assertIs(sr.sec, s, "SectionRef section stored incorrectly.")
        child = sr.child[0]
        self.assertIs(
            patch.objects.Section,
            type(child),
            "SectionRef.child should return Patch Section",
        )

    def test_section_access(self):
        from patch import transform

        s = p.Section()
        with s.push():
            r = p.SectionRef()
        self.assertEqual(
            transform(s), transform(r.section), "Argless SectionRef should return cas."
        )

    def test_bare_sec(self):
        from patch import transform

        s = p.Section()
        s2 = p.Section()
        s.connect(s2)
        s2.connect(s)
        sr = p.SectionRef(transform(s))
        _sr2 = p.SectionRef(sec=s2)
        self.assertIs(
            transform(sr.section),
            transform(s),
            "SectionRef section stored incorrectly.",
        )
        self.assertIs(
            patch.objects.Section,
            type(sr.section),
            "SectionRef with NRN sec didn't return wrapped sec.",
        )
        child = sr.child[0]
        self.assertIs(
            patch.objects.Section,
            type(child),
            "SectionRef.child should return Patch Section",
        )

    def test_wrong_args(self):
        self.assertRaises(TypeError, p.SectionRef, 2, 2)


class TestPointProcess(_shared.NeuronTestCase):
    def test_factory(self):
        s = p.Section()
        pp = p.ExpSyn(s(0.5))
        self.assertEqual(
            patch.objects.PointProcess,
            type(pp),
            "Point process factory did not return a PointProcess.",
        )
        self.assertTrue(
            str(pp.__neuron__()).find("ExpSyn[") != -1,
            "Point process factory did not return a NEURON point process pointer.",
        )

    def test_stimulate(self):
        s = p.Section()
        pp = p.ExpSyn(s(0.5))
        stim = pp.stimulate(start=0, number=1)
        stim._connections[pp].weight[0] = 0.4
        r = s.record()
        p.finitialize(-70)
        p.continuerun(10)
        self.assertAlmostEqual(list(r)[-1], -68.0, delta=0.1)
