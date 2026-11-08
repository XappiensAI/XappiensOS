"""Clipboard storage regressions; run with python3 -m unittest discover -s tests."""

from pathlib import Path
import sys
import unittest
from unittest import mock


LIB = Path(__file__).resolve().parents[1] / "config/xappiens-os/includes.chroot/usr/lib/xappiens"
sys.path.insert(0, str(LIB))
import clipboard_history as clipboard


TEXT = "text/plain;charset=utf-8"


class HistoryTests(unittest.TestCase):
    def assert_accounting(self, history):
        self.assertEqual(history.total_bytes, sum(len(entry.data) for entry in history.entries))

    def test_recopied_item_moves_to_front_without_duplicate_or_extra_bytes(self):
        history = clipboard.History()
        history.add(TEXT, "primero ñ".encode())
        history.add(TEXT, b"segundo")
        history.add(TEXT, "primero ñ".encode())
        self.assertEqual([entry.text for entry in history.entries], ["primero ñ", "segundo"])
        self.assert_accounting(history)

    def test_same_bytes_in_different_formats_remain_distinct(self):
        history = clipboard.History()
        history.add(TEXT, b"content")
        history.add("image/png", b"content")
        self.assertEqual(len(history.entries), 2)
        self.assertTrue(history.entries[0].is_image)
        self.assertFalse(history.entries[1].is_image)
        self.assertNotEqual(history.entries[0].digest, history.entries[1].digest)
        self.assert_accounting(history)

    def test_item_limit_discards_oldest_and_keeps_recent_duplicate(self):
        history = clipboard.History(max_items=2)
        for content in (b"one", b"two", b"one", b"three"):
            history.add(TEXT, content)
        self.assertEqual([entry.data for entry in history.entries], [b"three", b"one"])
        self.assert_accounting(history)

    def test_byte_limit_evicts_multiple_old_items(self):
        history = clipboard.History(max_bytes=10)
        for content in (b"one", b"two", b"three", b"sixsix"):
            history.add(TEXT, content)
        self.assertEqual([entry.data for entry in history.entries], [b"sixsix"])
        self.assert_accounting(history)

    def test_exact_byte_limit_is_accepted(self):
        history = clipboard.History(max_bytes=4)
        self.assertTrue(history.add(TEXT, b"1234"))
        self.assertEqual(history.total_bytes, 4)

    def test_oversized_item_does_not_destroy_existing_history(self):
        history = clipboard.History(max_bytes=10)
        history.add(TEXT, b"keep")
        with mock.patch.object(clipboard, "MAX_ITEM_BYTES", 5):
            self.assertFalse(history.add("image/png", b"123456"))
        self.assertFalse(history.add(TEXT, b"12345678901"))
        self.assertEqual([entry.data for entry in history.entries], [b"keep"])
        self.assert_accounting(history)

    def test_empty_and_whitespace_text_do_not_fill_history(self):
        history = clipboard.History()
        for content in (b"", b"\n", b" \t\r\n"):
            self.assertFalse(history.add(TEXT, content))
        self.assertEqual(history.entries, [])
        self.assert_accounting(history)

    def test_text_is_preserved_verbatim_including_newline_and_unicode(self):
        history = clipboard.History()
        content = "  <b>hola</b>\nsegunda línea 🔑\n".encode()
        self.assertTrue(history.add(TEXT, content))
        self.assertEqual(history.entries[0].data, content)
        self.assertEqual(history.entries[0].text, content.decode())

    def test_remove_updates_budget_and_missing_remove_is_safe(self):
        history = clipboard.History(max_bytes=8)
        history.add(TEXT, b"first")
        first = history.entries[0]
        history.add(TEXT, b"two")
        self.assertTrue(history.remove(first.digest))
        self.assertFalse(history.remove(first.digest))
        self.assertEqual([entry.data for entry in history.entries], [b"two"])
        self.assert_accounting(history)

    def test_clear_releases_budget_and_new_session_starts_empty(self):
        history = clipboard.History(max_bytes=5)
        history.add(TEXT, b"12345")
        history.clear()
        self.assertEqual(history.entries, [])
        self.assertEqual(history.total_bytes, 0)
        self.assertTrue(history.add(TEXT, b"again"))
        self.assertEqual(clipboard.History().entries, [])
        self.assert_accounting(history)

    def test_clipboard_contents_are_kept_without_filesystem_access(self):
        history = clipboard.History()
        with mock.patch("builtins.open", side_effect=AssertionError("disk access")), mock.patch(
            "os.open", side_effect=AssertionError("disk access")
        ):
            history.add(TEXT, b"temporary")
            history.add("image/png", b"\x89PNG\r\n\x1a\n")
            self.assertEqual(len(history.entries), 2)
            history.clear()
        self.assert_accounting(history)


if __name__ == "__main__":
    unittest.main()
