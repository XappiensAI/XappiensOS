"""Optional end-to-end test against an isolated, headless Wayland compositor.

Requires Sway, wtype, grim, wl-clipboard, GTK 3 and GtkLayerShell on PATH/the
library search path. Uses the real clipboard watchers, layer popup and paste
helper. All sockets, configuration, logs and screenshots live in a temporary
directory, and the private D-Bus session has no service autoactivation.
"""

import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import tempfile
import time
import unittest


APP = Path(__file__).resolve().parents[1] / "config/xappiens-os/includes.chroot/usr/lib/xappiens/clipboard-history"


def run_probe(args):
    sys.path.insert(0, str(APP.parent))
    loader = importlib.machinery.SourceFileLoader("clipboard_wayland_probe", str(APP))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)

    class Probe(module.ClipboardHistory):
        def do_startup(self):
            super().do_startup()
            self.target = module.Gtk.ApplicationWindow(application=self, title="Clipboard test target")
            self.target.set_default_size(450, 300)
            self.text = module.Gtk.TextView()
            self.target.add(self.text)
            self.target.show_all()
            self.target.present()
            self.text.grab_focus()
            module.GLib.idle_add(lambda: print("READY", flush=True))

        def do_command_line(self, command):
            args = command.get_arguments()[1:]
            if args == ["--snapshot"]:
                command.print_literal(json.dumps([(entry.mime, entry.data.hex()) for entry in self.history.entries]))
                return 0
            if args == ["--target"]:
                buffer = self.text.get_buffer()
                text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
                command.print_literal(json.dumps(text))
                return 0
            if args == ["--popup-visible"]:
                command.print_literal(json.dumps(bool(self.window and self.window.get_visible())))
                return 0
            if args == ["--show"]:
                self.toggle()
                return 0
            if args == ["--clear"]:
                self.clear_history()
                return 0
            if args == ["--quit"]:
                self.quit()
                return 0
            return super().do_command_line(command)

    return Probe().run(["clipboard-wayland-probe", *args])


def run_session():
    root = Path(os.environ["XDG_RUNTIME_DIR"])
    config = root / "sway.conf"
    config.write_text(
        "xwayland disable\noutput HEADLESS-1 mode 1280x800\n"
        "seat seat0 fallback true\nfocus_follows_mouse no\n"
    )
    env = os.environ.copy()
    env.update(
        WLR_BACKENDS="headless", WLR_RENDERER="pixman",
        WLR_LIBINPUT_NO_DEVICES="1", WLR_HEADLESS_OUTPUTS="1",
    )
    processes = []
    with (root / "sway.log").open("w+") as sway_log, (root / "app.log").open("w+") as app_log:
        try:
            sway = subprocess.Popen(
                ["sway", "--unsupported-gpu", "-c", str(config)],
                env=env, stdout=sway_log, stderr=sway_log,
            )
            processes.append(sway)
            deadline = time.monotonic() + 5
            sockets = []
            while time.monotonic() < deadline:
                sockets = [path for path in root.glob("wayland-*") if path.is_socket()]
                if sockets:
                    break
                if sway.poll() is not None:
                    raise AssertionError("Headless compositor exited before creating a socket")
                time.sleep(0.03)
            assert sockets, "Headless Wayland socket did not become ready"
            env.update(WAYLAND_DISPLAY=sockets[0].name, GDK_BACKEND="wayland")

            # Keep a keyboard device attached to the synthetic seat while
            # individual wtype/paste helper clients connect and disconnect.
            keeper = subprocess.Popen(["wtype", "-s", "30000"], env=env)
            processes.append(keeper)
            time.sleep(0.2)
            command = [sys.executable, __file__, "--probe"]

            def remote(*args):
                result = subprocess.run(
                    [*command, *args], env=env, capture_output=True, check=True, timeout=5,
                )
                return json.loads(result.stdout) if result.stdout else None

            def wait_for(predicate, message):
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    if predicate():
                        return
                    time.sleep(0.03)
                raise AssertionError(message)

            def copy(data, mime):
                subprocess.run(["wl-copy", "--type", mime], input=data, env=env, check=True, timeout=3)

            def keys(*args):
                subprocess.run(["wtype", *args], env=env, check=True, timeout=3)

            def show():
                remote("--show")
                wait_for(lambda: remote("--popup-visible"), "Popup did not open")
                time.sleep(0.2)  # Allow the compositor to focus the exclusive layer.

            server = subprocess.Popen(
                [*command, "--daemon"], env=env, stdout=subprocess.PIPE, stderr=app_log,
            )
            processes.append(server)
            assert select.select([server.stdout], [], [], 5)[0], "Clipboard daemon did not start"
            assert server.stdout.readline() == b"READY\n", "Clipboard daemon startup failed"
            time.sleep(0.3)
            keys("pre-")
            wait_for(lambda: remote("--target") == "pre-", "Test target did not receive keyboard input")

            ascii_text = b"ASCII clipboard"
            unicode_text = "Primera selección: áéí 🐧".encode()
            copy(ascii_text, "text/plain;charset=utf-8")
            wait_for(lambda: len(remote("--snapshot")) == 1, "ASCII clipboard content was not captured")
            copy(unicode_text, "text/plain;charset=utf-8")
            wait_for(lambda: len(remote("--snapshot")) == 2, "Unicode clipboard content was not captured")
            show()
            keys("-k", "Down", "-k", "Down", "-k", "Return")
            expected = "pre-" + ascii_text.decode()
            wait_for(lambda: remote("--target") == expected, "Selected ASCII text was not pasted into the prior window")
            wait_for(lambda: not remote("--popup-visible"), "Text selection did not close the popup")
            show()
            keys("-k", "Down", "-k", "Down", "-k", "Return")
            expected += unicode_text.decode()
            wait_for(lambda: remote("--target") == expected, "Selected Unicode text was not pasted verbatim")

            remote("--clear")
            assert remote("--snapshot") == [], "Clear left entries in the history"
            import gi
            gi.require_version("GdkPixbuf", "2.0")
            from gi.repository import GdkPixbuf

            image = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, 64, 64)
            image.fill(0x4488CCFF)
            ok, png = image.save_to_bufferv("png", [], [])
            assert ok
            copy(png, "image/png")
            wait_for(lambda: len(remote("--snapshot")) == 1, "PNG clipboard content was not captured")
            assert remote("--snapshot")[0][0] == "image/png"
            copy(b"newer clipboard text", "text/plain;charset=utf-8")
            wait_for(lambda: len(remote("--snapshot")) == 2, "Copy after the image was not captured")
            show()
            screenshot = root / "popup.png"
            subprocess.run(["grim", str(screenshot)], env=env, check=True, timeout=3)
            assert screenshot.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
            keys("-k", "Down", "-k", "Down", "-k", "Return")
            wait_for(lambda: not remote("--popup-visible"), "Image selection did not close the popup")
            restored = subprocess.run(
                ["wl-paste", "--no-newline", "--type", "image/png"],
                env=env, capture_output=True, check=True, timeout=3,
            )
            assert restored.stdout == png, "Restoring an older image changed its bytes"

            remote("--clear")
            copy(b"new session entry", "text/plain;charset=utf-8")
            wait_for(lambda: len(remote("--snapshot")) == 1, "Capture did not resume after clearing")
            show()
            keys("-k", "Escape")
            wait_for(lambda: not remote("--popup-visible"), "Escape did not close the popup")
            remote("--quit")
            assert server.wait(timeout=3) == 0, "Clipboard daemon did not shut down cleanly"
        except BaseException:
            for label, log in (("Sway", sway_log), ("Clipboard", app_log)):
                log.flush()
                log.seek(0)
                sys.stderr.write(f"{label}:\n{log.read()}")
            raise
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                if process.stdout:
                    process.stdout.close()


class ClipboardWaylandTest(unittest.TestCase):
    def test_real_popup_capture_and_paste(self):
        missing = [tool for tool in ("sway", "wtype", "grim", "wl-copy", "wl-paste", "dbus-run-session") if not shutil.which(tool)]
        if missing:
            self.skipTest("Optional Wayland tools unavailable: " + ", ".join(missing))
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            gi.require_version("GtkLayerShell", "0.1")
            from gi.repository import GtkLayerShell
            GtkLayerShell.get_major_version()
        except (ImportError, ValueError, AttributeError, OSError):
            self.skipTest("GTK 3 and GtkLayerShell are required for the optional Wayland test")

        with tempfile.TemporaryDirectory(prefix="xappiens-clipboard-wayland-") as tmp:
            env = os.environ.copy()
            for key in ("DISPLAY", "WAYLAND_DISPLAY", "SWAYSOCK"):
                env.pop(key, None)
            env.update(
                XDG_RUNTIME_DIR=tmp, XDG_CONFIG_HOME=f"{tmp}/config",
                XDG_CACHE_HOME=f"{tmp}/cache", XDG_DATA_HOME=f"{tmp}/data",
                NO_AT_BRIDGE="1", PYTHONDONTWRITEBYTECODE="1",
                XDG_CURRENT_DESKTOP="sway", XDG_SESSION_DESKTOP="sway",
                GTK_USE_PORTAL="0", GIO_USE_VFS="local",
            )
            # No service directories: this bus cannot autoactivate user services.
            bus = Path(tmp) / "bus.conf"
            bus.write_text(
                "<busconfig><type>session</type>"
                f"<listen>unix:tmpdir={tmp}</listen>"
                '<policy context="default"><allow send_destination="*" eavesdrop="true"/>'
                '<allow eavesdrop="true"/><allow own="*"/></policy></busconfig>'
            )
            result = subprocess.run(
                ["dbus-run-session", "--config-file=" + str(bus), "--", sys.executable, __file__, "--session"],
                env=env, capture_output=True, timeout=45,
            )
            if b"Failed to bind socket" in result.stderr and b"Operation not permitted" in result.stderr:
                self.skipTest("Sandbox blocks temporary D-Bus sockets; run outside sandbox")
            self.assertEqual(result.returncode, 0, result.stderr.decode())


if __name__ == "__main__":
    if sys.argv[1:2] == ["--probe"]:
        sys.exit(run_probe(sys.argv[2:]))
    elif sys.argv[1:2] == ["--session"]:
        run_session()
    else:
        unittest.main()
