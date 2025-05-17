import importlib.util
import os
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from click import ClickException
from click.testing import CliRunner

import glia._cli
import glia._fs
import glia._mpi
from glia import Mod, Package, get_cache_path

from . import _shared


def run_cli_command(command, xfail=False, **kwargs):
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(glia._cli.glia, command, **kwargs)
        if (
            not xfail
            and result.exception
            and not isinstance(result.exception, (SystemExit, ClickException))
        ):
            raise result.exception
        return result


def import_tmp_package(path):
    path = Path(path) / "__init__.py"
    spec = importlib.util.spec_from_file_location("__test_package__", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.package


class TestCLI(unittest.TestCase):
    """
    Test CLI commands
    """

    def test_glia(self):
        result = run_cli_command([])
        self.assertNotEqual("", result.output, "Should show help message")
        self.assertEqual(0, result.exit_code)

    @_shared.skipParallel
    @_shared.skipUnlessTestMods
    def test_compile(self):
        result = run_cli_command(["compile"])
        self.assertEqual(0, result.exit_code)
        self.assertRegex(result.output, r"(\d+) out of (\1) passed")

    @_shared.skipParallel
    @_shared.skipIfInstalled()
    def test_compile_nopkg(self):
        result = run_cli_command(["compile"])
        self.assertEqual(0, result.exit_code)
        self.assertRegex(result.output, r"0 out of 0 passed")

    def test_list(self):
        result = run_cli_command(["list"])
        self.assertEqual(0, result.exit_code)

    @_shared.skipUnlessTestMods
    def test_show(self):
        result = run_cli_command(["show", "AMPA"])
        self.assertEqual(0, result.exit_code)

    def test_show_unknown(self):
        result = run_cli_command(["show", "doesntexist"], xfail=True)
        self.assertIn('Unknown ASSET "doesntexist"', result.output)
        self.assertEqual(2, result.exit_code)

    @_shared.skipUnlessTestMods
    def test_show_pkg(self):
        # todo: test this test
        result = run_cli_command(["show-pkg", "glia_test_mods"])
        self.assertEqual(0, result.exit_code)

    def test_show_unknown_pkg(self):
        result = run_cli_command(["show-pkg", "doesntexist"], xfail=True)
        self.assertIn('Unknown PACKAGE "doesntexist"', result.output)
        self.assertEqual(2, result.exit_code)

    @_shared.skipUnlessTestMods
    def test_test(self):
        result = run_cli_command(["test", "Na"])

    @_shared.skipUnlessTestMods
    def test_test_unknown(self):
        result = run_cli_command(["test", "unknown"], xfail=True)
        self.assertIn("[?] unknown", result.output)
        self.assertEqual(1, result.exit_code)

    def test_cache(self):
        result = run_cli_command(["cache"])
        self.assertIn(
            glia._fs._install_dirs.user_cache_dir, result.output, "wrong cache dir"
        )

    @_shared.skipParallel
    def test_cache_clear(self):
        pre_test = glia._fs.read_cache()
        with TemporaryDirectory() as tmp:
            shutil.copytree(get_cache_path(), tmp, dirs_exist_ok=True)
            try:
                glia._fs.write_cache({"test_key": "test_value"})
                result = run_cli_command(["cache", "--clear"])
                self.assertFalse(Path(get_cache_path()).exists(), "cache dir not removed")
                self.assertNotIn("test_key", glia._fs.read_cache(), "cache not cleared")
            finally:
                glia._fs.write_cache(pre_test)
                shutil.copytree(tmp, get_cache_path(), dirs_exist_ok=True)


class TestPackagingCLI(unittest.TestCase):
    def test_new_package(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(glia._cli.glia, ["pkg", "new"], input="\n\n\n\n\n\n\n")
            self.assertEqual(
                ["glia_package"],
                os.listdir(),
                "Should have created the package folder",
            )
            self.assertIn(
                "glia_package",
                os.listdir("glia_package"),
                "Should have created the module folder",
            )
            os.chdir("glia_package")
            package = import_tmp_package("glia_package")
            self.assertEqual(Package, type(package))
            self.assertEqual(0, result.exit_code)

    def test_add_mod(self):
        mod_path = Path(__file__).parent / "data" / "mods" / "Na__0.mod"
        mod_source = mod_path.read_text()
        assert "SUFFIX Na\n" in mod_path.read_text(), "Source of Na was mutated"
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(glia._cli.glia, ["pkg", "new"], input="\n\n\n\n\n\n\n")
            os.chdir("./glia_package")
            result = runner.invoke(
                glia._cli.glia,
                ["pkg", "add", str(mod_path)],
            )

            self.assertEqual(0, result.exit_code)
            self.assertEqual(
                [".gitkeep", "Na__0.mod"], sorted(os.listdir("glia_package/mods"))
            )
            package = import_tmp_package("glia_package")
            self.assertEqual(Package, type(package), "Broken package declaration")
            self.assertEqual(1, len(package.mods), "Should have added mod")
            mod = package.mods[0]
            mod: Mod
            self.assertEqual(Mod, type(mod), "Broken mod declaration")
            self.assertEqual("Na", mod.asset_name, "Wrong name")
            self.assertEqual("0", mod.variant, "Wrong variant")
            self.assertEqual("glia_package", mod.pkg_name, "Wrong package name")
            self.assertEqual(
                "glia_package/mods/Na__0.mod",
                str(mod.path.relative_to(Path().resolve())),
                "Wrong mod path",
            )
            self.assertTrue(
                mod.path.exists(),
                "Mod path not created",
            )
            mod_text = mod.path.read_text()
            self.assertIn(f"SUFFIX {mod.mod_name}", mod_text, "Mod suffix not written")
            self.assertEqual(
                mod_source, mod_path.read_text(), "Adding mod file changed mod source"
            )

    def test_add_synapse(self):
        mod_path = Path(__file__).parent / "data" / "mods" / "AMPA__0.mod"
        mod_source = mod_path.read_text()
        assert (
            "POINT_PROCESS AMPA\n" in mod_path.read_text()
        ), "Source of AMPA was mutated"
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(glia._cli.glia, ["pkg", "new"], input="\n\n\n\n\n\n\n")
            os.chdir("./glia_package")
            result = runner.invoke(
                glia._cli.glia,
                [
                    "pkg",
                    "add",
                    str(mod_path),
                ],
            )

            self.assertEqual(0, result.exit_code)
            package = import_tmp_package("glia_package")
            mod = package.mods[0]
            mod: Mod
            mod_text = mod.path.read_text()
            self.assertIn(
                f"POINT_PROCESS {mod.mod_name}", mod_text, "Mod suffix not written"
            )
            self.assertEqual(
                mod_source, mod_path.read_text(), "Adding mod file changed mod source"
            )
