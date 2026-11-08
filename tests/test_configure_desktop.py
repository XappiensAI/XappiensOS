"""El atajo propio conserva upstream y nunca reemplaza configuración ajena."""

import importlib.machinery
import importlib.util
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest


SCRIPT = (Path(__file__).resolve().parents[1] / "config/xappiens-os/includes.chroot"
          / "usr/lib/xappiens/configure-desktop")
LOADER = importlib.machinery.SourceFileLoader("configure_desktop", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
desktop = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(desktop)


class DesktopConfigurationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "upstream"
        self.source.mkdir()
        self.original = '{\n    (modifiers: [Super], key: "t"): System(Terminal),\n}\n'
        (self.source / "defaults").write_text(self.original)
        (self.source / "system_actions").write_text('{Terminal: "cosmic-term"}\n')
        self.destination = self.root / "generated" / "v1"

    def test_preserves_upstream_and_copies_complete_directory(self):
        desktop.configure(self.source, self.destination)
        self.assertTrue(self.destination.is_symlink())
        self.assertEqual((self.source / "defaults").read_text(), self.original)
        self.assertIn('key: "t"', (self.destination / "defaults").read_text())
        self.assertIn(desktop.BINDING, (self.destination / "defaults").read_text())
        self.assertEqual((self.destination / "system_actions").read_bytes(),
                         (self.source / "system_actions").read_bytes())

    def test_idempotent_refresh_and_last_good_configuration(self):
        desktop.configure(self.source, self.destination)
        previous = self.destination.resolve()
        desktop.configure(self.source, self.destination)
        self.assertEqual(self.destination.resolve(), previous)
        (self.source / "system_actions").write_text('{Terminal: "new-terminal"}\n')
        desktop.configure(self.source, self.destination)
        self.assertNotEqual(self.destination.resolve(), previous)
        self.assertFalse(previous.exists())
        last_good = (self.destination / "defaults").read_bytes()
        (self.source / "defaults").write_text("unexpected new format")
        with self.assertRaises(ValueError):
            desktop.configure(self.source, self.destination)
        self.assertEqual((self.destination / "defaults").read_bytes(), last_good)

    def test_preserves_foreign_configuration_and_removes_only_own_generation(self):
        self.destination.mkdir(parents=True)
        sentinel = self.destination / "custom"
        sentinel.write_text("administrator's settings")
        with self.assertRaises(ValueError):
            desktop.configure(self.source, self.destination)
        with self.assertRaises(ValueError):
            desktop.remove(self.destination)
        self.assertEqual(sentinel.read_text(), "administrator's settings")
        sentinel.unlink()
        self.destination.rmdir()
        desktop.configure(self.source, self.destination)
        generation = self.destination.resolve()
        desktop.remove(self.destination)
        self.assertFalse(self.destination.exists())
        self.assertFalse(generation.exists())
        self.assertTrue(self.source.exists())

    def test_preserves_admin_edits_inside_generated_configuration(self):
        desktop.configure(self.source, self.destination)
        (self.destination / "defaults").write_text("administrator's override")
        with self.assertRaises(ValueError):
            desktop.configure(self.source, self.destination)
        with self.assertRaises(ValueError):
            desktop.remove(self.destination)
        self.assertEqual((self.destination / "defaults").read_text(),
                         "administrator's override")

    def test_profile_preserves_data_paths_and_does_not_duplicate(self):
        profile = SCRIPT.parents[3] / "etc/profile.d/xappiens-desktop.sh"
        # Sustituye systemctl; estas pruebas no acceden al gestor real del usuario.
        binaries = self.root / "bin"
        binaries.mkdir()
        fake_systemctl = binaries / "systemctl"
        fake_systemctl.write_text('#!/bin/sh\n'
                                  '[ "$*" = "--user import-environment XDG_DATA_DIRS" ] || exit 1\n'
                                  'printf %s "$XDG_DATA_DIRS" > "$XAPPIENS_TEST_ENV_FILE"\n')
        fake_systemctl.chmod(0o755)
        imported_environment = self.root / "imported-environment"
        for value, expected in (("", "/etc/xappiens:/usr/local/share:/usr/share"),
                                ("/custom:/usr/share", "/etc/xappiens:/custom:/usr/share"),
                                ("/etc/xappiens:/custom", "/etc/xappiens:/custom")):
            with self.subTest(value=value):
                env = dict(os.environ, XDG_DATA_DIRS=value,
                           PATH=str(binaries) + os.pathsep + os.environ.get("PATH", ""),
                           XAPPIENS_TEST_ENV_FILE=str(imported_environment))
                result = subprocess.run(["/bin/sh", "-c",
                                         '. "$1"; . "$1"; printf %s "$XDG_DATA_DIRS"',
                                         "test-profile", str(profile)],
                                        env=env, text=True, capture_output=True, check=True)
                self.assertEqual(result.stdout, expected)
                self.assertEqual(imported_environment.read_text(), expected)

    def test_user_environment_generator_preserves_and_quotes_data_paths(self):
        generator = (SCRIPT.parents[3]
                     / "usr/lib/systemd/user-environment-generators/90-xappiens-desktop")
        for value, expected in ((None, "/etc/xappiens:/usr/local/share:/usr/share"),
                                ("", "/etc/xappiens:/usr/local/share:/usr/share"),
                                ("/custom:/usr/share", "/etc/xappiens:/custom:/usr/share"),
                                ("/etc/xappiens:/custom", "/etc/xappiens:/custom"),
                                ("/custom data/á:/usr/share", "/etc/xappiens:/custom data/á:/usr/share")):
            with self.subTest(value=value):
                env = dict(os.environ)
                if value is None:
                    env.pop("XDG_DATA_DIRS", None)
                else:
                    env["XDG_DATA_DIRS"] = value
                result = subprocess.run([sys.executable, str(generator)], env=env,
                                        text=True, capture_output=True, check=True)
                # Los generadores producen asignaciones escapadas para el gestor.
                assignment, = shlex.split(result.stdout)
                self.assertEqual(assignment, "XDG_DATA_DIRS=" + expected)


if __name__ == "__main__":
    unittest.main()
