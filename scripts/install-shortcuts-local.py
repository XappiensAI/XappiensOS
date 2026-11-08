#!/usr/bin/python3
"""Install only the shortcut tool on a development desktop (no OS identity changes)."""

import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import sys


def install(home, migrate=False):
    source = Path(__file__).resolve().parents[1] / "config/xappiens-os/includes.chroot"
    library = home / ".local/lib/xappiens-shortcuts"
    library.mkdir(parents=True, exist_ok=True)
    for name in ("shortcuts", "shortcuts-ui.py", "xappiens_shortcuts.py", "paste-key"):
        destination = library / name
        shutil.copyfile(source / "usr/lib/xappiens" / name, destination)
        destination.chmod(0o755 if name in ("shortcuts", "paste-key") else 0o644)
    launcher = library / "shortcuts"
    binaries = home / ".local/bin"
    binaries.mkdir(parents=True, exist_ok=True)
    link = binaries / "xappiens-shortcuts"
    if link.is_symlink():
        link.unlink()
    elif link.exists():
        raise RuntimeError("Ya existe ~/.local/bin/xappiens-shortcuts; se ha conservado.")
    link.symlink_to(launcher)
    desktop = home / ".local/share/applications/com.xappiens.Shortcuts.desktop"
    desktop.parent.mkdir(parents=True, exist_ok=True)
    content = (source / "usr/share/applications/com.xappiens.Shortcuts.desktop").read_text()
    quoted = '"' + str(launcher).replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$") + '"'
    desktop.write_text(content.replace("/usr/lib/xappiens/shortcuts", quoted))
    desktop.chmod(0o644)
    migrated = 0
    if migrate:
        spec = importlib.util.spec_from_file_location("shortcuts_install_backend", library / "xappiens_shortcuts.py")
        backend = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backend)
        manager = backend.Manager(launcher=launcher)
        legacy = manager.config_home / "hotkey-paste/secrets"
        if legacy.is_file():
            # Parse data literally: never source a legacy secrets file as shell.
            values = dict(line.split("=", 1) for line in legacy.read_text().splitlines()
                          if "=" in line and not line.lstrip().startswith("#"))
            original = backend.read_file(manager.custom_path, "{}\n")
            entries, tail = backend.map_entries(original)
            replacements = []
            foreign = []
            for entry in entries:
                (modifiers, key), command = backend.binding(entry)
                slot = None
                for number in ("1", "2"):
                    script = str(home / "bin" / ("hotkey-paste-" + number))
                    if command in (script, "sh -c " + script, "sh " + script):
                        slot = number
                if slot and values.get(slot) and not values[slot].startswith("CHANGE_ME"):
                    replacements.append({"name": "Pegar texto " + slot, "type": "text",
                                         "text": values[slot], "key": key,
                                         "modifiers": list(modifiers)})
                else:
                    foreign.append(entry)
            if replacements:
                # Full rollback if registration fails; original scripts/data remain.
                old_state = backend.read_file(manager.state_path, None)
                backend.atomic_write(manager.custom_path.with_name("custom.before-shortcuts-migration"), original)
                try:
                    backend.atomic_write(manager.custom_path, "{" + "".join(e + "," for e in foreign) + tail + "\n}\n")
                    for action in replacements:
                        manager.save_action(action)
                        migrated += 1
                except BaseException:
                    backend.atomic_write(manager.custom_path, original)
                    if old_state is None:
                        manager.state_path.unlink(missing_ok=True)
                    else:
                        backend.atomic_write(manager.state_path, old_state)
                    raise
    print("Instalado: Atajos personalizados (menú de aplicaciones).")
    print(f"Acciones antiguas migradas: {migrated}. El contenido no se ha mostrado.")
    if Path("/etc/keyd/hotkey-paste.conf").exists():
        print("Pendiente: retirar la configuración antigua /etc/keyd/hotkey-paste.conf y recargar keyd; intercepta esas combinaciones.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--migrate-legacy", action="store_true", help="migrar los atajos hotkey-paste existentes, conservando copia")
    args = parser.parse_args()
    if os.getuid() == 0:
        parser.error("ejecuta este instalador como tu usuario, sin sudo")
    install(Path.home(), args.migrate_legacy)


if __name__ == "__main__":
    main()
