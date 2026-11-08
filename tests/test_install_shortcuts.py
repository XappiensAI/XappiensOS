"""Local upgrade/migration uses isolated home data and never evaluates snippets."""

import configparser
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "shortcuts_test_installer", REPO / "scripts/install-shortcuts-local.py")
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallShortcutsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="xappiens-shortcuts-install-test-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "user's home"
        self.home.mkdir()
        self.config = self.home / ".config"
        self.custom = self.config / "cosmic/com.system76.CosmicSettings.Shortcuts/v1/custom"
        self.state = self.config / "xappiens/shortcuts.json"
        self.library = self.home / ".local/lib/xappiens-shortcuts"

    def install(self, migrate=True):
        output = io.StringIO()
        with mock.patch.dict(os.environ, XDG_CONFIG_HOME=str(self.config)), \
                contextlib.redirect_stdout(output):
            installer.install(self.home, migrate=migrate)
        return output.getvalue()

    def write_legacy(self, text1="texto uno", text2="texto dos", duplicate=False):
        old1 = str(self.home / "bin/hotkey-paste-1")
        old2 = str(self.home / "bin/hotkey-paste-2")
        unrelated = '(modifiers: [Super, Shift], key: "s"): Spawn("capture-area")'
        second_key = "apostrophe" if duplicate else "ntilde"
        # Old desktop files used unquoted shell-style command strings; migration
        # only compares those strings and does not execute them.
        content = ("{\n"
                   '(modifiers: [Ctrl, Alt], key: "apostrophe"): Spawn('
                   + json.dumps("sh -c " + old1) + '),\n'
                   '(modifiers: [Ctrl, Alt], key: ' + json.dumps(second_key) + '): Spawn('
                   + json.dumps("sh -c " + old2) + '),\n'
                   + unrelated + ',\n}\n')
        self.custom.parent.mkdir(parents=True)
        self.custom.write_text(content)
        legacy = self.config / "hotkey-paste/secrets"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("# literal text values, never shell\n1=" + text1 + "\n2=" + text2 + "\n")
        legacy.chmod(0o600)
        return content, legacy, unrelated

    def test_installs_executable_launcher_and_application_entry(self):
        self.install(migrate=False)
        link = self.home / ".local/bin/xappiens-shortcuts"
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), self.library / "shortcuts")
        for name in ("shortcuts", "paste-key"):
            self.assertTrue(stat.S_IMODE((self.library / name).stat().st_mode) & 0o111)
        for name in ("shortcuts-ui.py", "xappiens_shortcuts.py"):
            self.assertTrue((self.library / name).is_file())
        desktop = self.home / ".local/share/applications/com.xappiens.Shortcuts.desktop"
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(desktop)
        self.assertEqual(parser["Desktop Entry"]["Name[es]"], "Atajos personalizados")
        self.assertEqual(parser["Desktop Entry"]["Exec"], '"' + str(self.library / "shortcuts") + '"')
        self.assertNotIn("/usr/lib/xappiens/shortcuts", desktop.read_text())
        self.assertFalse(self.state.exists())
        result = subprocess.run([str(link), "--help"], capture_output=True, text=True,
                                env=dict(os.environ, XDG_CONFIG_HOME=str(self.config)), timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--run", result.stdout)

    def test_migrates_literals_preserves_other_shortcuts_and_creates_backup(self):
        marker = self.home / "must-not-exist"
        text1 = "'$(touch " + str(marker) + ")' `id`; $HOME = literal ñ"
        text2 = "Otra cadena = con espacios 🐧"
        original, legacy, unrelated = self.write_legacy(text1, text2)
        legacy_bytes = legacy.read_bytes()
        output = self.install()
        self.assertFalse(marker.exists())
        self.assertNotIn(text1, output)
        self.assertNotIn(text2, output)
        state = json.loads(self.state.read_text())
        self.assertEqual({a["key"]: a["text"] for a in state["actions"]},
                         {"apostrophe": text1, "ntilde": text2})
        self.assertIn(unrelated, self.custom.read_text())
        self.assertNotIn("hotkey-paste-", self.custom.read_text())
        self.assertNotIn("must-not-exist", self.custom.read_text())
        self.assertEqual(legacy.read_bytes(), legacy_bytes)
        self.assertEqual(self.custom.with_name("custom.before-shortcuts-migration").read_text(), original)
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o600)

    def test_repeated_install_is_idempotent_and_preserves_action_identifiers(self):
        self.write_legacy()
        self.install()
        state = self.state.read_bytes()
        custom = self.custom.read_bytes()
        second_output = self.install()
        self.assertEqual(self.state.read_bytes(), state)
        self.assertEqual(self.custom.read_bytes(), custom)
        self.assertIn("migradas: 0", second_output)

    def test_migration_disabled_does_not_change_existing_shortcuts_or_data(self):
        original, legacy, _ = self.write_legacy()
        legacy_bytes = legacy.read_bytes()
        self.install(migrate=False)
        self.assertEqual(self.custom.read_text(), original)
        self.assertEqual(legacy.read_bytes(), legacy_bytes)
        self.assertFalse(self.state.exists())

    def test_failed_migration_restores_complete_original_configuration(self):
        original, legacy, _ = self.write_legacy(duplicate=True)
        legacy_bytes = legacy.read_bytes()
        with self.assertRaises(Exception) as raised:
            self.install()
        self.assertEqual(type(raised.exception).__name__, "ShortcutError")
        self.assertEqual(self.custom.read_text(), original)
        self.assertEqual(legacy.read_bytes(), legacy_bytes)
        self.assertFalse(self.state.exists())

    def test_placeholder_snippets_leave_legacy_binding_untouched(self):
        _, _, _ = self.write_legacy(text1="CHANGE_ME", text2="A valid snippet")
        self.install()
        state = json.loads(self.state.read_text())
        self.assertEqual(len(state["actions"]), 1)
        self.assertEqual(state["actions"][0]["key"], "ntilde")
        self.assertIn("hotkey-paste-1", self.custom.read_text())
        self.assertNotIn("hotkey-paste-2", self.custom.read_text())

    def test_existing_non_symlink_launcher_is_preserved(self):
        link = self.home / ".local/bin/xappiens-shortcuts"
        link.parent.mkdir(parents=True)
        link.write_text("existing user script")
        with self.assertRaises(RuntimeError):
            self.install(migrate=False)
        self.assertEqual(link.read_text(), "existing user script")


if __name__ == "__main__":
    unittest.main()
