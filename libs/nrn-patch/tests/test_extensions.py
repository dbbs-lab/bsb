import _shared


class TestExtensions(_shared.NeuronTestCase):
    """
    Test whether the extension system functions.
    """

    def test_vecstim(self):
        # Creating a VecStim here causes the test_network test to kill the process.
        # vc = p.VecStim(pattern=[1, 2, 3])
        pass
