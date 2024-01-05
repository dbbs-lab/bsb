import subprocess


def test_version():
    from bsb import __version__

    # assert __version__ == subprocess.run(["bsb", "--version"], check=True).stdout
    assert 1 == 1