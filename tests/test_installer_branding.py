"""Marca del instalador, logo, tema de GRUB y nombre de equipo por defecto."""

import importlib.util
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "packaging/xappiens-installer-branding"
ART = PKG / "files/usr/share/xappiens/installer"
LIB = REPO / "config/xappiens-os/includes.chroot/usr/lib/xappiens"
GRUB = REPO / "config/xappiens-os/grub-theme"

# Clases de ilustración que pone pop-installer en sus vistas (src/Views/*.vala)
ARTWORK_CLASSES = ["try-install", "language", "keyboard", "disks", "encrypt",
                   "progress", "success", "issue", "error", "create-account"]


def load_generator():
    spec = importlib.util.spec_from_file_location(
        "make_installer", REPO / "branding/installer/make-installer.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class InstallerCssTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = (ART / "gtk.css").read_text(encoding="utf-8")

    def test_every_artwork_class_has_our_image(self):
        for name in ARTWORK_CLASSES:
            with self.subTest(name=name):
                rule = re.search(r"\.artwork\.%s\s*\{([^}]*)\}" % re.escape(name), self.css)
                self.assertIsNotNone(rule, name)
                self.assertIn("file:///usr/share/xappiens/installer/", rule.group(1))

    def test_referenced_images_are_shipped(self):
        urls = set(re.findall(r'url\("file:///usr/share/xappiens/installer/([^"]+)"\)', self.css))
        self.assertTrue(urls)
        for name in urls:
            with self.subTest(name=name):
                self.assertTrue((ART / name).is_file(), name)

    def test_shipped_images_are_used(self):
        used = set(re.findall(r"installer/([a-z-]+-\d+\.png)", self.css))
        shipped = {p.name for p in ART.glob("*.png")}
        self.assertEqual(shipped - used, set())

    def test_keyframes_exist_for_animations(self):
        for name in re.findall(r"animation:\s*(xappiens-[a-z-]+)", self.css):
            with self.subTest(name=name):
                self.assertIn("@keyframes %s" % name, self.css)

    def test_css_parses_in_gtk(self):
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk
        except (ImportError, ValueError):
            self.skipTest("GTK3 no disponible")
        errors = []
        provider = Gtk.CssProvider()
        provider.connect("parsing-error", lambda _p, _s, err: errors.append(err.message))
        try:
            provider.load_from_data(self.css.encode())
        except Exception as exc:  # GLib.Error
            errors.append(str(exc))
        self.assertEqual(errors, [])


class GeneratedFilesTest(unittest.TestCase):
    """Los ficheros versionados coinciden con lo que genera make-installer.py."""

    @classmethod
    def setUpClass(cls):
        cls.gen = load_generator()

    def test_logo_svg_up_to_date(self):
        self.assertEqual(Path(self.gen.LOGO_SVG).read_text(encoding="utf-8"), self.gen.logo_svg())

    def test_installer_icon_up_to_date(self):
        self.assertEqual(Path(self.gen.INSTALLER_SVG).read_text(encoding="utf-8"),
                         self.gen.installer_svg())

    def test_avatar_up_to_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "avatar.png"
            self.gen.avatar().save(out)
            self.assertEqual(out.read_bytes(), Path(self.gen.AVATAR_PNG).read_bytes())

    def test_artwork_up_to_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, fn in self.gen.SCENES.items():
                for i, frame in enumerate(fn(), 1):
                    out = Path(tmp) / ("%s-%d.png" % (name, i))
                    frame.render().save(out)
                    with self.subTest(file=out.name):
                        self.assertEqual(out.read_bytes(), (ART / out.name).read_bytes())

    def test_grub_theme_complete(self):
        theme = (GRUB / "theme.txt").read_text(encoding="utf-8")
        for name in re.findall(r'"([a-z_*]+\.png)"', theme):
            if "*" in name:
                for part in ("c", "n", "s", "e", "w", "nw", "ne", "sw", "se"):
                    self.assertTrue((GRUB / name.replace("*", part)).is_file())
            else:
                self.assertTrue((GRUB / name).is_file(), name)


class IdentityTest(unittest.TestCase):
    def test_os_release_uses_our_logo(self):
        with tempfile.TemporaryDirectory() as root:
            subprocess.run([str(LIB / "write-identity")], check=True,
                           env=dict(os.environ, XAPPIENS_ROOT=root))
            text = (Path(root) / "etc/xappiens/os-release").read_text()
            self.assertIn("LOGO=distributor-logo-xappiens\n", text)


class DefaultHostnameTest(unittest.TestCase):
    def run_script(self, hostname, hosts):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(subprocess.run, ["rm", "-rf", str(root)])
        (root / "etc").mkdir()
        (root / "etc/hostname").write_text(hostname)
        (root / "etc/hosts").write_text(hosts)
        subprocess.run(["sh", str(LIB / "default-hostname")], check=True, capture_output=True,
                       env=dict(os.environ, XAPPIENS_ROOT=str(root)))
        return root

    def test_renames_pop_os(self):
        root = self.run_script("pop-os\n", "127.0.0.1\tlocalhost\n127.0.1.1\tpop-os.localdomain pop-os\n")
        self.assertEqual((root / "etc/hostname").read_text(), "xappiens-os\n")
        self.assertEqual((root / "etc/hosts").read_text(),
                         "127.0.0.1\tlocalhost\n127.0.1.1\txappiens-os.localdomain xappiens-os\n")
        self.assertTrue((root / "var/lib/xappiens/hostname-checked").exists())

    def test_keeps_other_names(self):
        root = self.run_script("mi-portatil\n", "127.0.1.1\tmi-portatil\n")
        self.assertEqual((root / "etc/hostname").read_text(), "mi-portatil\n")
        self.assertEqual((root / "etc/hosts").read_text(), "127.0.1.1\tmi-portatil\n")
        self.assertTrue((root / "var/lib/xappiens/hostname-checked").exists())


if __name__ == "__main__":
    unittest.main()
