"""Exercise real GApplication stdin forwarding on an isolated Broadway/DBus session.

GtkLayerShell is unused by the daemon and replaced only at import time. The
watchers are disabled in this probe, so it never accesses the user's clipboard.
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
import types
import unittest


APP = Path(__file__).resolve().parents[1] / "config/xappiens-os/includes.chroot/usr/lib/xappiens/clipboard-history"


def load_app(path):
    import gi
    import gi.repository

    original_require = gi.require_version

    def require(namespace, version):
        if namespace != "GtkLayerShell":
            original_require(namespace, version)

    gi.require_version = require
    gi.repository.GtkLayerShell = types.SimpleNamespace(
        init_for_window=lambda *_: None,
        set_namespace=lambda *_: None,
        set_layer=lambda *_: None,
        set_keyboard_mode=lambda *_: None,
        set_anchor=lambda *_: None,
        set_margin=lambda *_: None,
        Layer=types.SimpleNamespace(OVERLAY=0),
        KeyboardMode=types.SimpleNamespace(EXCLUSIVE=1),
        Edge=types.SimpleNamespace(BOTTOM=0, RIGHT=1),
    )
    sys.path.insert(0, str(Path(path).parent))
    loader = importlib.machinery.SourceFileLoader("clipboard_app_probe", path)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    module.MAX_ITEM_BYTES = 32
    return module


def run_probe_server(path, args):
    module = load_app(path)

    class Probe(module.ClipboardHistory):
        def do_startup(self):
            super().do_startup()
            module.GLib.idle_add(lambda: print("READY", flush=True))

        def check_watchers(self):
            return module.GLib.SOURCE_CONTINUE

        def do_command_line(self, command):
            args = command.get_arguments()[1:]
            if args == ["--snapshot"]:
                command.print_literal(json.dumps([entry.data.hex() for entry in self.history.entries]))
                return 0
            if args == ["--quit"]:
                self.quit()
                return 0
            if args == ["--exercise-ui"]:
                self.toggle()
                assert self.window.get_visible()
                self.capture("text", b"<b>plain text</b>\n")
                image = module.GdkPixbuf.Pixbuf.new(module.GdkPixbuf.Colorspace.RGB, False, 8, 2, 2)
                image.fill(0x4488CCFF)
                ok, png = image.save_to_bufferv("png", [], [])
                assert ok
                self.capture("image", png)
                assert self.history.entries[0].is_image
                self.search.set_text("no matching item")
                self.refresh()
                assert not hasattr(self.rows.get_row_at_index(0), "entry")
                self.search.set_text("")
                self.refresh()
                assert self.rows.get_row_at_index(0).entry.is_image

                # Dispatch real GTK key signals through the connected widgets:
                # entering the list keeps row zero, then arrows move one row.
                self.window.set_focus(self.search)
                # Broadway has no browser client in this headless probe. Send
                # GTK the focus event a real compositor would deliver.
                focus = module.Gdk.Event.new(module.Gdk.EventType.FOCUS_CHANGE)
                focus.in_ = True
                focus.window = self.search.get_window()
                self.search.send_focus_change(focus)
                assert self.search.has_focus()
                down = module.Gdk.Event.new(module.Gdk.EventType.KEY_PRESS)
                down.keyval = module.Gdk.KEY_Down
                down.window = self.search.get_window()
                down.set_device(module.Gdk.Display.get_default().get_default_seat().get_keyboard())
                assert self.search.emit("key-press-event", down)
                assert self.rows.get_selected_row().get_index() == 0
                assert self.window.get_focus() is self.rows.get_row_at_index(0)
                focus.in_ = False
                self.search.send_focus_change(focus)
                down.window = self.rows.get_window()
                assert self.rows.emit("key-press-event", down)
                assert self.rows.get_selected_row().get_index() == 1
                up = module.Gdk.Event.new(module.Gdk.EventType.KEY_PRESS)
                up.keyval = module.Gdk.KEY_Up
                up.window = self.rows.get_window()
                up.set_device(module.Gdk.Display.get_default().get_default_seat().get_keyboard())
                assert self.rows.emit("key-press-event", up)
                assert self.rows.get_selected_row().get_index() == 0

                # Enter on a focused button must retain the button action,
                # rather than triggering paste of the currently selected row.
                header = self.window.get_child().get_children()[0]
                clear = header.get_children()[1]
                self.window.set_focus(clear)
                activated = []
                original_activate = self.activate_selected
                self.activate_selected = lambda *_: activated.append(True)
                assert not self.on_key(self.window, types.SimpleNamespace(keyval=module.Gdk.KEY_Return))
                assert activated == []
                self.activate_selected = original_activate
                clear.clicked()
                assert self.history.entries == []
                assert all(state["cancel"].is_cancelled() for state in self.captures.values())
                self.hide()
                command.print_literal("ui-ok")
                return 0
            return super().do_command_line(command)

    return Probe().run(["clipboard-ipc-probe", *args])


def run_probe_session(path):
    command = [sys.executable, __file__, "--probe-server", path]

    def remote(*args, content=None, state=None, timeout=4):
        env = os.environ.copy()
        if state is not None:
            env["CLIPBOARD_STATE"] = state
        return subprocess.run(
            [*command, *args], input=content, capture_output=True,
            env=env, check=True, timeout=timeout,
        )

    def snapshot():
        return [bytes.fromhex(value) for value in json.loads(remote("--snapshot").stdout)]

    broadway = subprocess.Popen(
        ["broadwayd", "--unixsocket", str(Path(os.environ["XDG_RUNTIME_DIR"]) / "http"), ":79"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    server = None
    pending = None
    try:
        assert select.select([broadway.stdout], [], [], 3)[0], "Broadway did not start"
        assert b"Listening on " in broadway.stdout.readline(), broadway.stderr.read().decode()
        server = subprocess.Popen(
            [*command, "--daemon"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        assert select.select([server.stdout], [], [], 3)[0], "GTK daemon did not start"
        assert server.stdout.readline() == b"READY\n", server.stderr.read().decode()
        remote("--daemon")
        assert snapshot() == []
        remote("--capture", "text", content=b"first\n")
        assert snapshot() == [b"first\n"]
        for state in ("sensitive", "nil", "clear"):
            remote("--capture", "text", content=b"must not be stored", state=state)
        assert snapshot() == [b"first\n"]
        remote("--capture", "text", content=b"x" * 33)
        assert snapshot() == [b"first\n"]

        # A producer can leave its pipe open. Other remote commands must still
        # be serviced while capture waits for EOF, and partial data stays hidden.
        pending = subprocess.Popen(
            [*command, "--capture", "text"], stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        pending.stdin.write(b"late")
        pending.stdin.flush()
        time.sleep(0.2)
        assert snapshot() == [b"first\n"]
        remote("--daemon", timeout=2)
        pending.stdin.close()
        assert pending.wait(timeout=4) == 0, pending.stderr.read().decode()
        assert snapshot() == [b"late", b"first\n"]
        remote("--capture", "text", content=b"first\n")
        assert snapshot() == [b"first\n", b"late"]

        pending = subprocess.Popen(
            [*command, "--capture", "text"], stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        pending.stdin.write(b"discard on clear")
        pending.stdin.flush()
        time.sleep(0.2)
        assert remote("--exercise-ui").stdout == b"ui-ok"
        pending.stdin.close()
        assert pending.wait(timeout=4) == 0, pending.stderr.read().decode()
        assert snapshot() == []

        # A stuck owner must time out without publishing its partial contents.
        pending = subprocess.Popen(
            [*command, "--capture", "text"], stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        pending.stdin.write(b"discard on timeout")
        pending.stdin.flush()
        time.sleep(0.2)
        remote("--daemon", timeout=2)
        assert snapshot() == []
        assert pending.wait(timeout=7) == 0, pending.stderr.read().decode()
        pending.stdin.close()
        assert snapshot() == []
        remote("--quit")
        assert server.wait(timeout=3) == 0, server.stderr.read().decode()
        server = None
        print("IPC forwarding, sensitive states, bounded capture, slow stdin and GTK widgets passed")
    finally:
        for process in (pending, server, broadway):
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        if sys.exc_info()[0] is not None and server:
            sys.stderr.write(server.stderr.read().decode())


class ClipboardIpcTest(unittest.TestCase):
    def test_real_stdin_forwarding_does_not_block_daemon(self):
        if not shutil.which("broadwayd") or not shutil.which("dbus-run-session"):
            self.skipTest("Broadway and dbus-run-session are required")
        try:
            import gi
            gi.require_version("Gtk", "3.0")
        except (ImportError, ValueError):
            self.skipTest("PyGObject and GTK 3 are required")
        with tempfile.TemporaryDirectory(prefix="xappiens-clipboard-ipc-") as tmp:
            env = os.environ.copy()
            env.update(
                GDK_BACKEND="broadway", BROADWAY_DISPLAY=":79",
                XDG_RUNTIME_DIR=tmp, XDG_CONFIG_HOME=f"{tmp}/config",
                XDG_CACHE_HOME=f"{tmp}/cache", XDG_DATA_HOME=f"{tmp}/data",
                WAYLAND_DISPLAY="unused-probe", NO_AT_BRIDGE="1",
            )
            result = subprocess.run(
                ["dbus-run-session", "--", sys.executable, __file__, "--probe-session", str(APP)],
                env=env, capture_output=True, timeout=30,
            )
            if b"Failed to bind socket" in result.stderr and b"Operation not permitted" in result.stderr:
                self.skipTest("Sandbox blocks temporary D-Bus sockets; run outside sandbox")
            self.assertEqual(result.returncode, 0, result.stderr.decode())


if __name__ == "__main__":
    if sys.argv[1:2] == ["--probe-server"]:
        sys.exit(run_probe_server(sys.argv[2], sys.argv[3:]))
    elif sys.argv[1:2] == ["--probe-session"]:
        run_probe_session(sys.argv[2])
    else:
        unittest.main()
