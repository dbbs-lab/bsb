import unittest

from bsb_test import RandomStorageFixture, skip_nointernet, skip_parallel

from bsb import (
    MPI,
    Branch,
    CellType,
    Configuration,
    MissingMorphologyError,
    Morphology,
    NameSelector,
    Scaffold,
    SelectorError,
    StoredMorphology,
)


def spoof(*names):
    return [StoredMorphology(n, None, {"name": n}) for n in names]


def spoof_combo(name, *names):
    return [
        StoredMorphology(n, None, {"name": n})
        for n in [name + x for x in names] + [x + name for x in names]
    ]


class TestSelectors(RandomStorageFixture, unittest.TestCase, engine_name="hdf5"):
    def assertPicked(self, picks, sel, loaders, msg=None):
        self.assertEqual(picks, [l_.name for l_ in loaders if sel.pick(l_)], msg=msg)

    def test_strict_empty_name_selector(self):
        ns = NameSelector(names=[])
        all = spoof("A", "B", "*", "", "-", "0", "\\", "|", '"', ".*", "\\.")
        ns.validate(all)
        self.assertPicked([], ns, all, "Empty name selector should pick nothing")
        none = spoof()
        ns.validate(none)
        self.assertPicked([], ns, none, "Empty name selector should pick nothing")

    def test_strict_single_name_selector(self):
        ns = NameSelector(names=["B"])
        all = spoof("A", "B", "*", "", "-", "0", "\\", "|", '"', ".*", "\\.")
        ns.validate(all)
        self.assertPicked(["B"], ns, all, "Exact match to name expected")
        none = spoof()
        with self.assertRaises(MissingMorphologyError):
            ns.validate(none)

    def test_wild_single_name_selector(self):
        ns = NameSelector(names=["B*"])
        all = spoof_combo("B", "A", "B", "*", "-", "0", "\\", "|", '"', ".*", "\\.")
        all += spoof("", "B")
        ns.validate(all)
        exp = [
            "BA",
            "BB",
            "B*",
            "B-",
            "B0",
            "B\\",
            "B|",
            'B"',
            "B.*",
            "B\\.",
            "BB",
            "B",
        ]
        self.assertPicked(exp, ns, all, "Exact match to name expected")
        none = spoof()
        with self.assertRaises(MissingMorphologyError):
            ns.validate(none)
        ws = NameSelector(names=["*"])
        self.assertEqual(len(all), sum(map(ws.pick, all)), "wildcard should select all")

    # For some reason, under parallel conditions, likely due to the `morphologies.save`,
    # we deadlock.
    @skip_parallel
    def test_cell_type_shorthand(self):
        ct = CellType(spatial=dict(morphologies=[{"names": "*"}]))
        cfg = Configuration.default(cell_types={"ct": ct})
        s = Scaffold(cfg, self.storage)
        s.morphologies.save("A", Morphology([Branch([[0, 0, 0]], [1])]), overwrite=True)
        self.assertEqual(1, len(ct.get_morphologies()), "Should select saved morpho")
        ct.spatial.morphologies[0].names = ["B"]
        with self.assertRaises(MissingMorphologyError):
            self.assertEqual(0, len(ct.get_morphologies()), "should select 0 morpho")

    @skip_nointernet
    def test_nm_selector(self):
        name = "H17-03-013-11-08-04_692297214_m"
        ct = CellType(
            spatial=dict(
                morphologies=[
                    {
                        "select": "from_neuromorpho",
                        "names": [name],
                    }
                ]
            )
        )
        cfg = Configuration.default(cell_types={"ct": ct})
        s = Scaffold(cfg, self.storage)
        self.assertIn(name, s.morphologies, "missing NM")
        m = s.morphologies.select(*ct.spatial.morphologies)[0]
        self.assertEqual(name, m.get_meta()["neuron_name"], "meta not stored")

    @skip_nointernet
    def test_nm_selector_wrong_name(self):
        ct = CellType(
            spatial=dict(
                morphologies=[
                    {
                        "select": "from_neuromorpho",
                        "names": ["H17-03-013-11-08-04_692297214_m"],
                    }
                ]
            )
        )
        cfg = Configuration.default(cell_types={"ct": ct})
        Scaffold(cfg, self.storage)
        with self.assertRaises(SelectorError, msg="doesnt exist, should error"):
            err = None
            try:
                ct.spatial.morphologies[0] = {
                    "select": "from_neuromorpho",
                    "names": ["H17-03-013-11-08-04_692297214_m", "H17-03-092297214_m"],
                }
            except Exception as e:
                err = e
            err = MPI.bcast(err, root=0)
            if err:
                raise err
        with self.assertRaises(SelectorError, msg="doesnt exist, should error"):
            err = None
            try:
                ct.spatial.morphologies[0] = {
                    "select": "from_neuromorpho",
                    "names": ["H17-03-092297214_m"],
                }
            except SelectorError as e:
                err = e
            err = MPI.bcast(err, root=0)
            if err:
                raise err
