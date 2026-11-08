"""Atajos persistentes: conservar COSMIC y mantener el texto fuera de comandos.

Todos los archivos y contenidos usados aquí son de prueba y viven en /tmp.
Estas pruebas no conectan con la sesión gráfica ni envían pulsaciones.
"""

import importlib.util
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import stat
import sys
import tempfile
import unittest
from unittest import mock
import uuid


BACKEND = (Path(__file__).resolve().parents[1]
           / "config/xappiens-os/includes.chroot/usr/lib/xappiens/xappiens_shortcuts.py")
SPEC = importlib.util.spec_from_file_location("shortcuts_test_backend", BACKEND)
shortcuts = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = shortcuts
SPEC.loader.exec_module(shortcuts)


class ShortcutsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="xappiens-shortcuts-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "config"
        self.launcher = self.root / "our tools" / "shortcuts"
        self.manager = shortcuts.Manager(config_home=self.config, launcher=self.launcher)
        self.state = self.config / "xappiens/shortcuts.json"
        self.custom = self.config / "cosmic/com.system76.CosmicSettings.Shortcuts/v1/custom"

    def action(self, **overrides):
        action = dict(name="Pegar texto", key="apostrophe", modifiers=["Ctrl", "Alt"],
                      type="text", text="Una cadena de prueba")
        action.update(overrides)
        return action

    def save(self, **overrides):
        action = self.action()
        action.update(overrides)
        return self.manager.save_action(action)

    def write_custom(self, value):
        self.custom.parent.mkdir(parents=True, exist_ok=True)
        self.custom.write_text(value, encoding="utf-8")

    def files_snapshot(self):
        return {str(path.relative_to(self.config)): path.read_bytes()
                for path in self.config.rglob("*") if path.is_file() and path.suffix != ".lock"}

    def spawn_commands(self):
        # Generated Spawn strings contain only ASCII paths/UUIDs in this suite.
        values = re.findall(r'Spawn\(("(?:[^"\\]|\\.)*")\)',
                            self.custom.read_text(encoding="utf-8"))
        return [json.loads(value) for value in values]

    def test_create_persist_edit_and_delete_preserves_foreign_bindings(self):
        foreign = '''    // Keep this comment, including its comma.
    (
        modifiers: [Super, Shift],
        key: "s",
        description: Some("Capture: [area], {window}"),
    ): Spawn("printf 'one,two: [three] {four}'"),
    /* Keep a block comment: , } ] */
    (modifiers: [Super], key: "t"): System(Terminal),'''
        self.write_custom("{\n" + foreign + "\n}\n")
        identifier = self.save()
        self.assertEqual(uuid.UUID(identifier).hex, identifier.replace("-", ""))
        created = self.manager.list_actions()
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["id"], identifier)
        self.assertEqual(created[0]["text"], "Una cadena de prueba")
        for marker in ("Keep this comment, including its comma.",
                       'description: Some("Capture: [area], {window}")',
                       'Spawn("printf \'one,two: [three] {four}\'")',
                       "Keep a block comment: , } ]", "System(Terminal)"):
            self.assertIn(marker, self.custom.read_text())

        updated = dict(created[0], name="Otro texto", key="F10", text="Actualizado")
        self.assertEqual(self.manager.save_action(updated), identifier)
        reopened = shortcuts.Manager(config_home=self.config, launcher=self.launcher)
        self.assertEqual(reopened.list_actions()[0]["text"], "Actualizado")
        self.assertEqual(reopened.list_actions()[0]["key"], "F10")
        self.assertEqual(sum(identifier in command for command in self.spawn_commands()), 1)

        reopened.delete_action(identifier)
        self.assertEqual(reopened.list_actions(), [])
        self.assertNotIn(identifier, self.custom.read_text())
        for marker in ("Keep this comment, including its comma.",
                       "Keep a block comment: , } ]", "System(Terminal)"):
            self.assertIn(marker, self.custom.read_text())

    def test_text_is_exact_unicode_multiline_data_never_a_spawn_argument(self):
        text = "Primera: áéí ñ 🐧\nSegunda: ' y \\\" y =\n$(touch /tmp/never-run) `id`; $HOME\n"
        identifier = self.save(text=text)
        self.assertEqual(self.manager.list_actions()[0]["text"], text)
        persisted = json.loads(self.state.read_text())
        self.assertEqual(persisted["actions"][0]["text"], text)
        command, = self.spawn_commands()
        self.assertEqual(shlex.split(command), [str(self.launcher), "--run", identifier])
        self.assertNotIn("never-run", self.custom.read_text())
        self.assertNotIn("Primera", self.custom.read_text())

    def test_launcher_path_with_spaces_and_quotes_is_one_command_argument(self):
        launcher = self.root / "user's tools" / "shortcuts"
        manager = shortcuts.Manager(config_home=self.config, launcher=launcher)
        identifier = manager.save_action(self.action())
        command, = self.spawn_commands()
        self.assertEqual(shlex.split(command), [str(launcher), "--run", identifier])

    def test_duplicate_owned_combination_is_rejected_without_changing_files(self):
        self.save()
        before = self.files_snapshot()
        with self.assertRaises(shortcuts.ShortcutError):
            self.save(name="Otro atajo", modifiers=["Alt", "Ctrl"], text="Otro texto")
        self.assertEqual(self.files_snapshot(), before)

    def test_duplicate_foreign_combination_is_rejected_without_changing_files(self):
        self.write_custom('''{
    (modifiers: [Alt, Ctrl], key: "apostrophe", description: Some("Foreign")):
        Spawn("do-something"),
}
''')
        before = self.files_snapshot()
        with self.assertRaises(shortcuts.ShortcutError):
            self.save()
        self.assertEqual(self.files_snapshot(), before)

    def test_editing_one_action_cannot_take_another_actions_combination(self):
        first = self.save()
        second = self.save(name="Segundo", key="F10")
        before = self.files_snapshot()
        updated = dict(next(a for a in self.manager.list_actions() if a["id"] == second),
                       key="apostrophe")
        self.assertEqual(updated["id"], second)
        with self.assertRaises(shortcuts.ShortcutError):
            self.manager.save_action(updated)
        self.assertEqual(self.files_snapshot(), before)
        self.assertIn(first, {a["id"] for a in self.manager.list_actions()})

    def test_malformed_cosmic_configuration_is_preserved(self):
        for malformed in ("not a RON map", "{\n", '{(modifiers: [Ctrl], key: "unterminated): Spawn("oops")}',
                          '{(modifiers: [Ctrl], key: "a"):}',
                          '{(modifiers: [Ctrl], key: ): Spawn("oops")}'):
            with self.subTest(malformed=malformed):
                self.write_custom(malformed)
                before = self.files_snapshot()
                with self.assertRaises(shortcuts.ShortcutError):
                    self.save()
                self.assertEqual(self.files_snapshot(), before)

    def test_corrupt_action_storage_is_not_replaced(self):
        self.save()
        self.state.write_text("{ broken JSON")
        before = self.files_snapshot()
        with self.assertRaises(shortcuts.ShortcutError):
            self.save(key="F10")
        self.assertEqual(self.files_snapshot(), before)

    def test_action_storage_missing_identifiers_is_rejected(self):
        self.save()
        state = json.loads(self.state.read_text())
        del state["actions"][0]["id"]
        self.state.write_text(json.dumps(state))
        before = self.files_snapshot()
        with self.assertRaises(shortcuts.ShortcutError):
            self.manager.list_actions()
        self.assertEqual(self.files_snapshot(), before)

    def test_symlink_configuration_does_not_modify_its_target(self):
        target = self.root / "outside-config"
        original = '{(modifiers: [Super], key: "t"): System(Terminal)}'
        target.write_text(original)
        self.custom.parent.mkdir(parents=True)
        self.custom.symlink_to(target)
        with self.assertRaises(shortcuts.ShortcutError):
            self.save()
        self.assertTrue(self.custom.is_symlink())
        self.assertEqual(target.read_text(), original)

    def test_symlink_action_storage_does_not_modify_its_target(self):
        target = self.root / "outside-actions"
        original = '{"version":1,"actions":[]}'
        target.write_text(original)
        self.state.parent.mkdir(parents=True)
        self.state.symlink_to(target)
        with self.assertRaises(shortcuts.ShortcutError):
            self.save()
        self.assertTrue(self.state.is_symlink())
        self.assertEqual(target.read_text(), original)

    def test_invalid_keys_and_modifiers_do_not_register_shortcuts(self):
        self.save()
        for changes in ({"key": "not_a_real_keysym"}, {"modifiers": ["MetaOops"]},
                        {"type": "unknown"}):
            with self.subTest(changes=changes):
                before = self.files_snapshot()
                with self.assertRaises(shortcuts.ShortcutError):
                    self.save(**changes)
                self.assertEqual(self.files_snapshot(), before)

    def test_configuration_containing_saved_text_is_private(self):
        self.save()
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.custom.stat().st_mode), 0o600)

    def test_command_action_registers_only_runner_and_does_not_execute_on_save(self):
        marker = self.root / "must-not-exist"
        command = "touch " + shlex.quote(str(marker))
        identifier = self.save(type="command", command=command)
        self.assertFalse(marker.exists())
        action, = self.manager.list_actions()
        self.assertEqual(action["command"], command)
        spawn, = self.spawn_commands()
        self.assertEqual(shlex.split(spawn), [str(self.launcher), "--run", identifier])

    def test_second_manager_preserves_actions_saved_since_its_creation(self):
        second_manager = shortcuts.Manager(config_home=self.config, launcher=self.launcher)
        self.assertEqual(second_manager.list_actions(), [])
        first = self.save()
        second = second_manager.save_action(self.action(key="F10", name="Segundo"))
        self.assertEqual({a["id"] for a in self.manager.list_actions()}, {first, second})

    def runtime_environment(self):
        return mock.patch.dict(os.environ, WAYLAND_DISPLAY="private-test-socket",
                               XDG_RUNTIME_DIR=str(self.root))

    def test_paste_sends_bytes_over_stdin_to_both_selections_then_helper(self):
        text = "Pegar ñ 🐧\n'$(never execute)'\n"
        identifier = self.save(text=text)
        with self.runtime_environment(), mock.patch.object(shortcuts.os, "getuid", return_value=1000), \
                mock.patch.object(shortcuts.time, "sleep"), \
                mock.patch.object(shortcuts.subprocess, "run", return_value=mock.Mock(returncode=0)) as run:
            self.manager.run_action(identifier)
        self.assertEqual(run.call_count, 3)
        first, primary, helper = run.call_args_list
        self.assertEqual(first.args[0], ["wl-copy", "--type", "text/plain;charset=utf-8"])
        self.assertEqual(primary.args[0], ["wl-copy", "--primary", "--type", "text/plain;charset=utf-8"])
        self.assertEqual(first.kwargs["input"], text.encode("utf-8"))
        self.assertEqual(primary.kwargs["input"], text.encode("utf-8"))
        self.assertEqual(Path(helper.args[0][0]).name, "paste-key")
        self.assertEqual(len(helper.args[0]), 1)
        for call in (first, primary, helper):
            self.assertNotIn("shell", call.kwargs)

    def test_clipboard_failure_does_not_inject_a_paste_chord(self):
        identifier = self.save()
        for failure_index in (0, 1):
            with self.subTest(failure_index=failure_index):
                responses = [mock.Mock(returncode=0)] * failure_index + [mock.Mock(returncode=1)]
                with self.runtime_environment(), mock.patch.object(shortcuts.os, "getuid", return_value=1000), \
                        mock.patch.object(shortcuts.subprocess, "run", side_effect=responses) as run:
                    with self.assertRaises(shortcuts.ShortcutError):
                        self.manager.run_action(identifier)
                self.assertEqual(run.call_count, failure_index + 1)
                self.assertTrue(all(call.args[0][0] == "wl-copy" for call in run.call_args_list))

    def test_helper_failure_reports_manual_paste_available(self):
        identifier = self.save()
        with self.runtime_environment(), mock.patch.object(shortcuts.os, "getuid", return_value=1000), \
                mock.patch.object(shortcuts.time, "sleep"), \
                mock.patch.object(shortcuts.subprocess, "run", side_effect=[
                    mock.Mock(returncode=0), mock.Mock(returncode=0), mock.Mock(returncode=1)]):
            with self.assertRaisesRegex(shortcuts.ShortcutError, "Ctrl.*V"):
                self.manager.run_action(identifier)

    def test_command_actions_explicitly_launch_shell_without_pasting(self):
        command = "printf 'an explicit command'"
        identifier = self.save(type="command", command=command)
        with mock.patch.object(shortcuts.os, "getuid", return_value=1000), \
                mock.patch.object(shortcuts.subprocess, "Popen") as popen, \
                mock.patch.object(shortcuts.subprocess, "run") as run:
            self.manager.run_action(identifier)
        self.assertEqual(popen.call_args.args[0], ["/bin/sh", "-c", command])
        run.assert_not_called()

    def test_root_and_missing_wayland_fail_before_pasting(self):
        identifier = self.save()
        with mock.patch.object(shortcuts.os, "getuid", return_value=0), \
                mock.patch.object(shortcuts.subprocess, "run") as run:
            with self.assertRaises(shortcuts.ShortcutError):
                self.manager.run_action(identifier)
            run.assert_not_called()
        environment = {key: value for key, value in os.environ.items() if key != "WAYLAND_DISPLAY"}
        with mock.patch.dict(os.environ, environment, clear=True), \
                mock.patch.object(shortcuts.os, "getuid", return_value=1000), \
                mock.patch.object(shortcuts.subprocess, "run") as run:
            with self.assertRaises(shortcuts.ShortcutError):
                self.manager.run_action(identifier)
            run.assert_not_called()

    def test_overlapping_paste_does_not_interleave_clipboards_or_keystrokes(self):
        identifier = self.save()
        with (self.root / "xappiens-shortcuts-paste.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.runtime_environment(), mock.patch.object(shortcuts.os, "getuid", return_value=1000), \
                    mock.patch.object(shortcuts.subprocess, "run") as run:
                self.manager.run_action(identifier)
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
