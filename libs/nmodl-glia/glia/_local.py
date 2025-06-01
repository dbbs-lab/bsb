import subprocess
import sys
from pathlib import Path

from glia._fs import get_local_pkg_path, log


def create_local_package():
    from cookiecutter.main import cookiecutter

    dir = Path(get_local_pkg_path())

    cookiecutter(
        str((Path(__file__).parent / "packaging/cookiecutter-glia").resolve()),
        extra_context={
            "full_name": "You",
            "email": "na@example.com",
            "project_name": "Local asset collection",
            "project_slug": "local",
            "version": "1.0.0",
            "open_source_license": "Not open source",
        },
        no_input=True,
        output_dir=dir.parent,
    )

    install_package(dir)


def install_package(path: Path):
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", str(path)],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        e.args = (*e.args, e.stderr.decode("utf-8"))
        log("Failed to install local package", exc=e)
