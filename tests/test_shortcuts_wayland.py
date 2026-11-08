"""Optional real-COSMIC shortcut test, nested in an isolated headless Sway.

The outer compositor supplies physical key codes to COSMIC's Spanish layout.
No connection is made to the user's compositor, clipboard or session bus.
"""

import json
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest


APP_DIR = Path(__file__).resolve().parents[1] / "config/xappiens-os/includes.chroot/usr/lib/xappiens"
EXTRACTED = Path("/tmp/xappiens-readme-capture-deps/root/usr")
SAMPLE = "Primera línea: áéí ñ 🐧\nSegunda línea: ' \" $HOME `literal`"


class PhysicalKeys:
    """A full evdev-map keyboard on outer Sway, seen as physical keys by winit.

    wtype uses compact maps with arbitrary codes, unsuitable for a nested
    compositor which interprets physical codes with its own Spanish layout.
    """

    def __init__(self, socket):
        loader = importlib.machinery.SourceFileLoader("shortcut_paste_protocol", str(APP_DIR / "paste-key"))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        p = importlib.util.module_from_spec(spec)
        loader.exec_module(p)
        self.p = p
        c = p.C
        wl = c.CDLL("libwayland-client.so.0")
        self.wl = wl
        wl.wl_display_connect.argtypes = [c.c_char_p]
        wl.wl_display_connect.restype = c.c_void_p
        wl.wl_display_disconnect.argtypes = [c.c_void_p]
        wl.wl_display_roundtrip.argtypes = [c.c_void_p]
        wl.wl_display_roundtrip.restype = c.c_int
        wl.wl_proxy_add_listener.argtypes = [c.c_void_p, c.POINTER(c.c_void_p), c.c_void_p]
        wl.wl_proxy_add_listener.restype = c.c_int
        wl.wl_proxy_destroy.argtypes = [c.c_void_p]
        wl.wl_proxy_marshal_flags.argtypes = [c.c_void_p, c.c_uint, p.InterfacePointer, c.c_uint, c.c_uint]
        wl.wl_proxy_marshal_flags.restype = c.c_void_p
        self.marshal = wl.wl_proxy_marshal_flags
        self.registry_type = p.WlInterface.in_dll(wl, "wl_registry_interface")
        self.seat_type = p.WlInterface.in_dll(wl, "wl_seat_interface")
        self.keyboard_methods = (p.WlMessage * 4)(
            p.WlMessage(b"keymap", b"uhu", None), p.WlMessage(b"key", b"uuu", None),
            p.WlMessage(b"modifiers", b"uuuu", None), p.WlMessage(b"destroy", b"", None))
        self.keyboard_type = p.WlInterface(b"zwp_virtual_keyboard_v1", 1, 4, self.keyboard_methods, 0, None)
        self.create_types = (p.InterfacePointer * 2)(c.pointer(self.seat_type), c.pointer(self.keyboard_type))
        self.manager_methods = (p.WlMessage * 1)(p.WlMessage(b"create_virtual_keyboard", b"on", self.create_types))
        self.manager_type = p.WlInterface(b"zwp_virtual_keyboard_manager_v1", 1, 1, self.manager_methods, 0, None)
        self.globals = {}
        self.added = p.GlobalCallback(lambda _d, _r, n, i, v: self.globals.setdefault(i, (n, v)))
        self.removed = p.RemoveCallback(lambda *_args: None)
        self.listener = (c.c_void_p * 2)(c.cast(self.added, c.c_void_p).value,
                                        c.cast(self.removed, c.c_void_p).value)
        self.display = wl.wl_display_connect(str(socket).encode())
        assert self.display, "Cannot connect to private outer Wayland socket"
        self.registry = self.marshal(self.display, 1, c.pointer(self.registry_type), 1, 0, c.c_void_p())
        assert not wl.wl_proxy_add_listener(self.registry, self.listener, None)
        self.roundtrip()

        def bind(interface):
            name, _version = self.globals[interface.name]
            return self.marshal(self.registry, 0, c.pointer(interface), 1, 0,
                                c.c_uint(name), c.c_char_p(interface.name), c.c_uint(1), c.c_void_p())

        self.seat = bind(self.seat_type)
        self.manager = bind(self.manager_type)
        self.keyboard = self.marshal(self.manager, 0, c.pointer(self.keyboard_type), 1, 0,
                                     c.c_void_p(self.seat), c.c_void_p())
        keymap, _shift = p.standard_keymap()
        fd = os.memfd_create("xappiens-test-keymap", os.MFD_CLOEXEC)
        try:
            os.write(fd, keymap)
            self.marshal(self.keyboard, 0, None, 1, 0, c.c_uint(1), c.c_int(fd), c.c_uint(len(keymap)))
            self.roundtrip()
        finally:
            os.close(fd)
        self.held = set()

    def roundtrip(self):
        assert self.wl.wl_display_roundtrip(self.display) >= 0, "Outer Wayland disconnected"

    def key(self, code, pressed):
        c = self.p.C
        self.marshal(self.keyboard, 1, None, 1, 0,
                     c.c_uint(int(time.monotonic() * 1000) & 0xffffffff), c.c_uint(code), c.c_uint(pressed))
        if pressed:
            self.held.add(code)
        else:
            self.held.discard(code)
        mask = (1 if 42 in self.held else 0) | (4 if 29 in self.held else 0) | (8 if 56 in self.held else 0)
        self.marshal(self.keyboard, 2, None, 1, 0, c.c_uint(mask), c.c_uint(0), c.c_uint(0), c.c_uint(0))
        self.roundtrip()
        time.sleep(0.05)

    def tap(self, *codes):
        for code in codes:
            self.key(code, 1)
            self.key(code, 0)

    def shortcut(self, code=12, held_seconds=0):
        self.key(29, 1)
        self.key(56, 1)
        self.tap(code)  # AE11=12: apostrophe; AC11=40: dead_acute in Spanish.
        time.sleep(held_seconds)
        self.key(56, 0)
        self.key(29, 0)

    def close(self):
        for code in list(self.held):
            self.key(code, 0)
        self.marshal(self.keyboard, 3, None, 1, 1)
        self.roundtrip()
        for proxy in (self.manager, self.seat, self.registry):
            self.wl.wl_proxy_destroy(proxy)
        self.wl.wl_display_disconnect(self.display)


def target():
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib, Gtk

    state = Path(os.environ["XDG_RUNTIME_DIR"]) / "target.json"
    window = Gtk.Window(title="Xappiens shortcuts test target")
    window.set_default_size(600, 350)
    view = Gtk.TextView()
    window.add(view)
    buffer = view.get_buffer()

    def snapshot(*_args):
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
        temporary = state.with_suffix(".tmp")
        temporary.write_text(json.dumps(text), encoding="utf-8")
        temporary.replace(state)

    buffer.connect("changed", snapshot)
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    window.present()
    view.grab_focus()
    GLib.idle_add(snapshot)
    Gtk.main()


def run_session():
    root = Path(os.environ["XDG_RUNTIME_DIR"])
    config_home = Path(os.environ["XDG_CONFIG_HOME"])
    sys.path.insert(0, str(APP_DIR))
    from xappiens_shortcuts import Manager

    manager = Manager(config_home=config_home, launcher=APP_DIR / "shortcuts")
    action = {"name": "Prueba de pegado", "modifiers": ["Ctrl", "Alt"],
              "key": "apostrophe", "type": "text", "text": SAMPLE}
    comp_config = config_home / "cosmic/com.system76.CosmicComp/v1"
    comp_config.mkdir(parents=True, exist_ok=True)
    (comp_config / "xkb_config").write_text(
        '(rules: "", model: "", layout: "es", variant: "", '
        'options: Some("lv3:ralt_switch,compose:rctrl"), '
        'repeat_delay: 600, repeat_rate: 25)\n'
    )
    sway_config = root / "sway.conf"
    sway_config.write_text("xwayland disable\noutput HEADLESS-1 mode 1280x800\n"
                           "seat seat0 fallback true\nfocus_follows_mouse no\n")
    env = os.environ.copy()
    env.update(WLR_BACKENDS="headless", WLR_RENDERER="pixman",
               WLR_LIBINPUT_NO_DEVICES="1", WLR_HEADLESS_OUTPUTS="1")
    processes = []
    physical = None

    def wait_for(predicate, message, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.05)
        snapshot = root / "target.json"
        if snapshot.exists():
            message += " (synthetic target=" + repr(json.loads(snapshot.read_text())) + ")"
        raise AssertionError(message)

    with (root / "sway.log").open("w+") as sway_log, \
            (root / "cosmic.log").open("w+") as cosmic_log, \
            (root / "target.log").open("w+") as target_log:
        try:
            sway = subprocess.Popen([os.environ["TEST_SWAY"], "--unsupported-gpu", "-c", str(sway_config)],
                                    env=env, stdout=sway_log, stderr=sway_log)
            processes.append(sway)
            wait_for(lambda: any(p.is_socket() for p in root.glob("wayland-*")),
                     "Headless Sway did not create a Wayland socket")
            outer_socket = next(p.name for p in root.glob("wayland-*") if p.is_socket())
            outer_env = env | {"WAYLAND_DISPLAY": outer_socket}
            physical = PhysicalKeys(root / outer_socket)
            time.sleep(0.2)
            cosmic_env = outer_env | {"COSMIC_BACKEND": "winit", "WINIT_UNIX_BACKEND": "wayland",
                                      "LIBGL_ALWAYS_SOFTWARE": "1"}
            cosmic = subprocess.Popen(["cosmic-comp", "--no-xwayland"], env=cosmic_env,
                                      stdout=cosmic_log, stderr=cosmic_log)
            processes.append(cosmic)
            wait_for(lambda: any(p.is_socket() and p.name != outer_socket for p in root.glob("wayland-*")),
                     "Nested COSMIC did not create a Wayland socket")
            inner_socket = next(p.name for p in root.glob("wayland-*")
                                if p.is_socket() and p.name != outer_socket)
            inner_env = env | {"WAYLAND_DISPLAY": inner_socket, "GDK_BACKEND": "wayland"}
            # Wait for COSMIC's backend to finish initializing after socket creation.
            time.sleep(1)
            probe = subprocess.Popen([sys.executable, __file__, "--target"], env=inner_env,
                                     stdout=target_log, stderr=target_log)
            processes.append(probe)
            snapshot = root / "target.json"
            wait_for(snapshot.exists, "GTK test target did not open")
            time.sleep(0.6)

            def text():
                return json.loads(snapshot.read_text(encoding="utf-8"))

            physical.tap(25, 19, 18)  # pre
            wait_for(lambda: text() == "pre", "COSMIC target did not receive physical key events")
            # First-time setup happens with COSMIC already running, just as in the GUI.
            # No shortcuts namespace or custom file was prepared before startup.
            identifier = manager.save_action(action)
            time.sleep(0.6)  # Allow cosmic-config's filesystem watcher to reload.
            # On the outer US keymap minus is physical AE11: apostrophe in Spanish.
            # Keep the modifiers held well past the action's paste delay.
            physical.shortcut(held_seconds=0.9)
            expected = "pre" + SAMPLE
            wait_for(lambda: text() == expected,
                     "Ctrl+Alt+apostrophe did not paste Unicode/multiline text exactly")
            # Input from the physical source must restore Spanish layout and clear modifiers.
            physical.tap(25, 24, 31, 20, 12)  # post' in Spanish
            expected += "post'"
            wait_for(lambda: text() == expected,
                     "Normal typing after paste has stuck modifiers or the wrong keyboard layout")
            # The same shortcut must work again after physical input restored the keymap.
            physical.shortcut()
            expected += SAMPLE
            wait_for(lambda: text() == expected, "The custom shortcut did not work a second time")
            # Editing an existing action must work without restarting the compositor.
            updated = SAMPLE + "\nActualizado en la misma sesión."
            manager.save_action(action | {"id": identifier, "text": updated})
            time.sleep(0.6)
            physical.shortcut()
            expected += updated
            wait_for(lambda: text() == expected, "Editing a live shortcut did not update its text")
            # Deletion must stop pasting; an unbound base key may still reach GTK.
            manager.delete_action(identifier)
            time.sleep(0.6)
            physical.shortcut()
            time.sleep(0.8)
            after_delete = text()
            assert after_delete.startswith(expected) and len(after_delete) <= len(expected) + 1, \
                "Deleting the live shortcut did not stop its text action"
            # The Spanish accent key directly right of ñ is a different key
            # from the apostrophe on the number row. Both must be bindable.
            accent_action = action | {"name": "Prueba tecla de acento", "key": "dead_acute"}
            manager.save_action(accent_action)
            time.sleep(0.6)
            physical.shortcut(code=40, held_seconds=0.9)
            expected = after_delete + SAMPLE
            wait_for(lambda: text() == expected,
                     "Ctrl+Alt+dead_acute (right of ñ) did not paste the exact text")
            # An intercepted dead key must not leave a pending accent behind.
            physical.tap(18)  # e
            expected += "e"
            wait_for(lambda: text() == expected,
                     "Using the dead_acute shortcut left an accent or modifiers pending")
        except BaseException:
            for label, log in (("Sway", sway_log), ("COSMIC", cosmic_log), ("Target", target_log)):
                log.flush()
                log.seek(0)
                sys.stderr.write(f"{label}:\n{log.read()[-14000:]}")
            raise
        finally:
            if physical is not None:
                try:
                    physical.close()
                except (AssertionError, OSError):
                    pass  # The compositor may already have disconnected after a failure.
            for process in reversed(processes):
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()


class ShortcutsCosmicTest(unittest.TestCase):
    def test_spanish_shortcut_pastes_in_real_cosmic(self):
        sway = shutil.which("sway") or str(EXTRACTED / "bin/sway")
        missing = [tool for tool in ("cosmic-comp", "wl-copy", "dbus-run-session")
                   if not shutil.which(tool)]
        if not Path(sway).is_file():
            missing.append("sway")
        if missing:
            self.skipTest("Optional COSMIC test tools unavailable: " + ", ".join(missing))
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk
            Gtk.get_major_version()
        except (ImportError, ValueError):
            self.skipTest("GTK3 is required for the optional COSMIC test")

        with tempfile.TemporaryDirectory(prefix="xappiens-shortcuts-cosmic-") as temporary:
            root = Path(temporary)
            env = os.environ.copy()
            for name in ("DISPLAY", "WAYLAND_DISPLAY", "SWAYSOCK", "DBUS_SESSION_BUS_ADDRESS",
                         "COSMIC_SESSION_SOCK", "XDG_ACTIVATION_TOKEN", "DESKTOP_STARTUP_ID"):
                env.pop(name, None)
            env.update(XDG_RUNTIME_DIR=temporary, XDG_CONFIG_HOME=str(root / "config"),
                       XDG_CACHE_HOME=str(root / "cache"), XDG_DATA_HOME=str(root / "data"),
                       XDG_STATE_HOME=str(root / "state"), HOME=str(root / "home"),
                       XDG_DATA_DIRS="/usr/local/share:/usr/share", TEST_SWAY=sway,
                       NO_AT_BRIDGE="1", GTK_USE_PORTAL="0", GIO_USE_VFS="local",
                       PYTHONDONTWRITEBYTECODE="1", XDG_CURRENT_DESKTOP="COSMIC")
            if str(EXTRACTED) in sway:
                env["LD_LIBRARY_PATH"] = str(EXTRACTED / "lib/x86_64-linux-gnu")
            bus = root / "bus.conf"
            bus.write_text('<busconfig><type>session</type>'
                           f'<listen>unix:tmpdir={temporary}</listen>'
                           '<policy context="default"><allow send_destination="*" eavesdrop="true"/>'
                           '<allow eavesdrop="true"/><allow own="*"/></policy></busconfig>')
            result = subprocess.run(["dbus-run-session", "--config-file=" + str(bus), "--",
                                     sys.executable, __file__, "--session"], env=env,
                                    capture_output=True, timeout=50)
            if b"Failed to bind socket" in result.stderr and b"Operation not permitted" in result.stderr:
                self.skipTest("Sandbox blocks temporary D-Bus sockets; run outside sandbox")
            self.assertEqual(result.returncode, 0, result.stderr.decode())


if __name__ == "__main__":
    if sys.argv[1:] == ["--target"]:
        target()
    elif sys.argv[1:] == ["--session"]:
        run_session()
    else:
        unittest.main()
