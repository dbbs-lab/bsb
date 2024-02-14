import subprocess


def test_version():
    from bsb import __version__

    assert f"bsb {__version__}" == subprocess.check_output(
        ["bsb", "--version"]
    ).strip().decode("utf-8")
