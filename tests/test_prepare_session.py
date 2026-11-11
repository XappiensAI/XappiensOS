"""Login handover and legacy cleanup, with no access to the real session bus."""

import importlib.machinery
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "config/xappiens-os/includes.chroot/usr/lib/xappiens/prepare-session"
LOADER = importlib.machinery.SourceFileLoader("prepare_session", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
session = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(session)

LEGACY = """[Unit]
Description=ydotool daemon (virtual keyboard for hotkey paste)
After=default.target
[Service]
Type=simple
ExecStart=/usr/bin/ydotoold
Restart=on-failure
RestartSec=2
# Socket por defecto: /tmp/.ydotool_socket
[Install]
WantedBy=default.target
"""


class PrepareSessionTests(unittest.TestCase):
    def test_waits_only_for_a_new_cosmic_wayland_session(self):
        env = {"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "COSMIC"}
        self.assertTrue(session.is_new_cosmic_session(env))
        for changes in ({"WAYLAND_DISPLAY": "wayland-1"},
                        {"XDG_SESSION_TYPE": "tty"},
                        {"XDG_CURRENT_DESKTOP": "GNOME"},
                        {"XDG_CURRENT_DESKTOP": "NOTCOSMIC"}):
            self.assertFalse(session.is_new_cosmic_session(dict(env, **changes)))

    def test_waits_for_release_and_does_not_use_a_fixed_delay(self):
        running = mock.Mock(side_effect=[True, True, False])
        sleep = mock.Mock()
        self.assertTrue(session.wait_for_greeter(984, running=running, sleep=sleep))
        self.assertEqual(sleep.call_count, 2)
        sleep.reset_mock()
        self.assertTrue(session.wait_for_greeter(984, running=lambda uid: False,
                                                sleep=sleep))
        sleep.assert_not_called()

    def test_a_stuck_greeter_cannot_prevent_login_indefinitely(self):
        now = [0.0]
        def sleep(delay):
            now[0] += delay
        result = session.wait_for_greeter(984, timeout=0.2, running=lambda uid: True,
                                          clock=lambda: now[0], sleep=sleep)
        self.assertFalse(result)
        self.assertAlmostEqual(now[0], 0.2)

    def test_login_profile_invokes_preparation_only_before_cosmic_is_running(self):
        root = Path(self.temp.name)
        marker = root / "called"
        helper = root / "prepare"
        helper.write_text('#!/bin/sh\ntouch "$XAPPIENS_TEST_MARKER"\n')
        helper.chmod(0o755)
        profile = root / "profile"
        source = SCRIPT.parents[3] / "etc/profile.d/xappiens-desktop.sh"
        profile.write_text(source.read_text().replace("/usr/lib/xappiens/prepare-session", str(helper)))
        systemctl = root / "systemctl"
        systemctl.write_text("#!/bin/sh\nexit 0\n")
        systemctl.chmod(0o755)
        for desktop, kind, display, expected in (
                ("COSMIC", "wayland", "", True),
                ("COSMIC", "wayland", "wayland-1", False),
                ("COSMIC", "tty", "", False),
                ("GNOME", "wayland", "", False)):
            with self.subTest(desktop=desktop, kind=kind, display=display):
                marker.unlink(missing_ok=True)
                env = dict(os.environ, XDG_CURRENT_DESKTOP=desktop,
                           XDG_SESSION_TYPE=kind, WAYLAND_DISPLAY=display,
                           XAPPIENS_TEST_MARKER=str(marker),
                           PATH=str(root) + os.pathsep + os.environ["PATH"])
                subprocess.run(["/bin/sh", "-c", '. "$1"', "profile-test", str(profile)],
                               env=env, check=True, capture_output=True, timeout=5)
                self.assertEqual(marker.exists(), expected)

    def test_proc_scan_ignores_other_users_zombies_and_disappearing_processes(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            for pid, uid, state, name in [(10, 984, "Z", "cosmic-comp"),
                                          (11, 1000, "S", "cosmic-comp"),
                                          (12, 984, "S", "other")]:
                (proc / str(pid)).mkdir()
                (proc / str(pid) / "status").write_text(
                    f"Name:\t{name}\nState:\t{state} (state)\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\n")
            (proc / "13").mkdir()
            self.assertFalse(session.greeter_is_running(984, proc))
            (proc / "13/status").write_text(
                "Name:\tcosmic-comp\nState:\tS (sleeping)\nUid:\t984\t984\t984\t984\n")
            self.assertTrue(session.greeter_is_running(984, proc))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = Path(self.temp.name) / "config"
        self.binary = Path(self.temp.name) / "ydotoold"
        self.unit = self.config / "systemd/user/ydotoold.service"
        self.unit.parent.mkdir(parents=True)
        self.unit.write_text(LEGACY)
        self.link = self.unit.parent / "default.target.wants/ydotoold.service"
        self.link.parent.mkdir()
        self.link.symlink_to(self.unit)
        self.run = mock.Mock(return_value=subprocess.CompletedProcess(
            [], 0, f"FragmentPath={self.unit}\nDropInPaths=\n", ""))

    def cleanup(self):
        return session.retire_missing_legacy_service(self.config, self.binary, self.run)

    def test_disables_broken_legacy_unit_but_preserves_file_for_rollback(self):
        self.assertTrue(self.cleanup())
        self.assertEqual(self.unit.read_text(), LEGACY)
        self.assertEqual(self.run.call_args_list[1].args[0],
                         ["systemctl", "--user", "disable", "--now", "ydotoold.service"])

    def test_leaves_a_working_installation_alone(self):
        self.binary.touch()
        self.assertFalse(self.cleanup())
        self.run.assert_not_called()

    def test_preserves_customized_units_and_overrides(self):
        for text in (LEGACY.replace("RestartSec=2", "RestartSec=5"),
                     LEGACY.replace("/usr/bin/ydotoold", "/usr/local/bin/ydotoold")):
            self.unit.write_text(text)
            self.assertFalse(self.cleanup())
        self.run.assert_not_called()
        self.unit.write_text(LEGACY)
        self.run.return_value.stdout += "DropInPaths=/etc/systemd/user/ydotoold.service.d/custom.conf\n"
        self.assertFalse(self.cleanup())
        self.assertEqual(self.run.call_count, 1)

    def test_preserves_an_already_disabled_unit_or_different_loaded_unit(self):
        self.link.unlink()
        self.assertFalse(self.cleanup())
        self.run.assert_not_called()
        self.link.symlink_to(self.unit)
        self.run.return_value.stdout = "FragmentPath=/etc/systemd/user/ydotoold.service\nDropInPaths=\n"
        self.assertFalse(self.cleanup())
        self.assertEqual(self.run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
