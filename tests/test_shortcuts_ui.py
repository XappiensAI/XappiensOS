"""Keyboard labels must distinguish Spanish apostrophe and acute-accent keys."""

import importlib.util
from pathlib import Path
import sys
import unittest


APP_DIR = Path(__file__).resolve().parents[1] / "config/xappiens-os/includes.chroot/usr/lib/xappiens"


class ShortcutKeyNamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            gi.require_version("Gdk", "3.0")
        except (ImportError, ValueError):
            raise unittest.SkipTest("GTK3 is required for shortcut input parsing")
        sys.path.insert(0, str(APP_DIR))
        try:
            spec = importlib.util.spec_from_file_location("shortcuts_ui_test", APP_DIR / "shortcuts-ui.py")
            cls.ui = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.ui)
        finally:
            sys.path.remove(str(APP_DIR))

    def test_apostrophe_and_accent_are_distinct_spanish_keys(self):
        self.assertEqual(self.ui.parse_shortcut("Ctrl+Alt+'"),
                         {"key": "apostrophe", "modifiers": ["Ctrl", "Alt"]})
        self.assertEqual(self.ui.parse_shortcut("Ctrl+Alt+´"),
                         {"key": "dead_acute", "modifiers": ["Ctrl", "Alt"]})

    def test_accent_key_has_readable_label_and_lossless_edit_expression(self):
        action = {"key": "dead_acute", "modifiers": ["Ctrl", "Alt"]}
        self.assertEqual(self.ui.shortcut_label(action), "Ctrl + Alt + ´")
        self.assertEqual(self.ui.parse_shortcut(self.ui.shortcut_expression(action)), action)

    def test_shifted_accent_is_still_its_base_key(self):
        self.assertEqual(self.ui.parse_shortcut("Ctrl+Alt+Shift+´"),
                         {"key": "dead_acute", "modifiers": ["Ctrl", "Alt", "Shift"]})


if __name__ == "__main__":
    unittest.main()
