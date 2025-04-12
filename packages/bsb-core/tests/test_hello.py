"""Hello unit test module."""

from bsb_core.hello import hello


def test_hello():
    """Test the hello function."""
    assert hello() == "Hello bsb-core"
