"""User-owned COSMIC actions. Text never becomes a shell command."""

import contextlib
import ctypes
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import time
import uuid


MODIFIERS = ("Ctrl", "Alt", "Shift", "Super")
MAX_TEXT_BYTES = 1024 * 1024
MAX_CONFIG_BYTES = 4 * MAX_TEXT_BYTES


class ShortcutError(Exception):
    pass


def ron_quote(value):
    escapes = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t"}
    return '"' + ''.join(escapes.get(c, f"\\u{{{ord(c):x}}}" if ord(c) < 32 else c)
                         for c in value) + '"'


def tokens(source):
    """RON tokens with spans; comments and strings cannot split map entries."""
    result = []
    i = 0
    while i < len(source):
        start = i
        if source[i].isspace():
            i += 1
            continue
        if source.startswith("//", i):
            end = source.find("\n", i)
            i = len(source) if end < 0 else end + 1
            continue
        if source.startswith("/*", i):
            depth = 1
            i += 2
            while i < len(source) and depth:
                if source.startswith("/*", i):
                    depth += 1
                    i += 2
                elif source.startswith("*/", i):
                    depth -= 1
                    i += 2
                else:
                    i += 1
            if depth:
                raise ShortcutError("La configuración de COSMIC tiene un comentario sin cerrar.")
            continue
        raw = re.match(r'r(#+)?"', source[i:])
        if raw:
            prefix = raw.group(0)
            end_marker = '"' + (raw.group(1) or "")
            end = source.find(end_marker, i + len(prefix))
            if end < 0:
                raise ShortcutError("La configuración de COSMIC tiene una cadena sin cerrar.")
            value = source[i + len(prefix):end]
            i = end + len(end_marker)
            result.append(("string", value, start, i))
            continue
        if source[i] == '"':
            i += 1
            value = ""
            while i < len(source) and source[i] != '"':
                if source[i] == "\\":
                    i += 1
                    if i >= len(source):
                        break
                    escaped = source[i]
                    if escaped == "u":
                        match = re.match(r'u\{([0-9a-fA-F]{1,6})\}', source[i:])
                        if not match:
                            raise ShortcutError("Escape Unicode inválido en la configuración de COSMIC.")
                        try:
                            value += chr(int(match[1], 16))
                        except ValueError as error:
                            raise ShortcutError("Escape Unicode inválido en COSMIC.") from error
                        i += len(match[0])
                        continue
                    escapes = {'n': '\n', 'r': '\r', 't': '\t', '0': '\0', '\\': '\\', '"': '"', "'": "'"}
                    if escaped not in escapes:
                        raise ShortcutError("Escape inválido en la configuración de COSMIC.")
                    value += escapes[escaped]
                else:
                    value += source[i]
                i += 1
            if i >= len(source):
                raise ShortcutError("La configuración de COSMIC tiene una cadena sin cerrar.")
            i += 1
            result.append(("string", value, start, i))
            continue
        match = re.match(r'[A-Za-z_][A-Za-z_0-9]*', source[i:])
        if match:
            i += len(match[0])
            result.append(("name", match[0], start, i))
        else:
            i += 1
            result.append(("punct", source[start:i], start, i))
    return result


def map_entries(source):
    parts = tokens(source)
    if not parts or parts[0][1] != "{" or parts[-1][1] != "}":
        raise ShortcutError("No se reconoce la configuración de atajos de COSMIC; se ha conservado.")
    entries = []
    stack = []
    start = parts[0][3]
    for kind, value, begin, end in parts[1:-1]:
        if kind == "punct":
            if value in "([{":
                stack.append(value)
            elif value in ")]}":
                if not stack or stack.pop() != {")": "(", "]": "[", "}": "{"}[value]:
                    raise ShortcutError("La configuración de atajos de COSMIC está incompleta.")
            elif value == "," and not stack:
                entries.append(source[start:begin])
                start = end
    if stack:
        raise ShortcutError("La configuración de atajos de COSMIC está incompleta.")
    tail = source[start:parts[-1][2]]
    if tokens(tail):
        entries.append(tail)
        tail = ""
    for entry in entries:
        binding(entry)  # Refuse unknown key structures before changing the map.
    return entries, tail


def binding(entry):
    parts = tokens(entry)
    if not parts or parts[0][1] != "(":
        raise ShortcutError("No se reconoce un atajo de COSMIC; se ha conservado la configuración.")
    key = None
    modifiers = None
    close = next((i for i, t in enumerate(parts)
                  if t[1] == ")" and i + 1 < len(parts) and parts[i + 1][1] == ":"), None)
    if close is None or close + 2 >= len(parts):
        raise ShortcutError("No se reconoce un atajo de COSMIC.")
    for i, token in enumerate(parts[:close]):
        if token[:2] == ("name", "key"):
            if i + 2 >= close or parts[i + 1][1] != ":":
                raise ShortcutError("Tecla de COSMIC no reconocida.")
            if parts[i + 2][0] == "string":
                key = parts[i + 2][1]
            elif parts[i + 2][1] != "None":
                raise ShortcutError("Tecla de COSMIC no reconocida.")
        if token[:2] == ("name", "modifiers") and i + 2 < close and parts[i + 1][1] == ":":
            if parts[i + 2][1] != "[":
                raise ShortcutError("Modificadores de COSMIC no reconocidos.")
            modifiers = []
            for item in parts[i + 3:close]:
                if item[1] == "]":
                    break
                if item[0] == "name":
                    modifiers.append(item[1])
    # A few upstream bindings have no key (key: None); preserve them too.
    spawn = None
    action = parts[close + 2:]
    if len(action) == 4 and [t[1] for t in action[:2]] == ["Spawn", "("] and action[2][0] == "string" and action[3][1] == ")":
        spawn = action[2][1]
    if modifiers is None:
        raise ShortcutError("Atajo de COSMIC sin modificadores reconocibles.")
    return (frozenset(modifiers), key), spawn


def canonical_key(name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_]+', name):
        raise ShortcutError("La tecla no es válida; vuelve a capturar la combinación.")
    xkb = ctypes.CDLL("libxkbcommon.so.0")
    xkb.xkb_keysym_from_name.argtypes = [ctypes.c_char_p, ctypes.c_int]
    xkb.xkb_keysym_from_name.restype = ctypes.c_uint
    xkb.xkb_keysym_to_lower.argtypes = [ctypes.c_uint]
    xkb.xkb_keysym_to_lower.restype = ctypes.c_uint
    xkb.xkb_keysym_get_name.argtypes = [ctypes.c_uint, ctypes.c_char_p, ctypes.c_size_t]
    symbol = xkb.xkb_keysym_from_name(name.encode(), 0)
    if not symbol:
        raise ShortcutError("COSMIC no reconoce esa tecla.")
    buffer = ctypes.create_string_buffer(128)
    xkb.xkb_keysym_get_name(xkb.xkb_keysym_to_lower(symbol), buffer, len(buffer))
    return buffer.value.decode()


def read_file(path, default):
    if path.is_symlink():
        raise ShortcutError("La configuración es un enlace simbólico; no se modificó.")
    try:
        if path.stat().st_size > MAX_CONFIG_BYTES:
            raise ShortcutError("La configuración es demasiado grande.")
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return default


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + "-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Manager:
    def __init__(self, config_home=None, launcher=None):
        self.config_home = Path(config_home or os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        self.directory = self.config_home / "xappiens"
        self.state_path = self.directory / "shortcuts.json"
        self.custom_path = self.config_home / "cosmic/com.system76.CosmicSettings.Shortcuts/v1/custom"
        self.launcher = str(Path(launcher or Path(__file__).with_name("shortcuts")).resolve())

    @contextlib.contextmanager
    def locked(self):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(self.directory / ".shortcuts.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def load(self):
        try:
            state = json.loads(read_file(self.state_path, '{"version":1,"actions":[]}'))
            if state.get("version") != 1 or not isinstance(state.get("actions"), list):
                raise ValueError()
            if "launcher" in state and not isinstance(state["launcher"], str):
                raise ValueError()
            identifiers = set()
            combinations = set()
            actions = []
            for action in state["actions"]:
                validated = self.validate(action)
                identifier = validated["id"]
                combination = (tuple(validated["modifiers"]), validated["key"])
                if identifier in identifiers or combination in combinations:
                    raise ValueError()
                identifiers.add(identifier)
                combinations.add(combination)
                actions.append(validated)
            state["actions"] = actions
            return state
        except (ValueError, TypeError, AttributeError, KeyError) as error:
            raise ShortcutError("No se pudo leer la configuración de acciones; se ha conservado.") from error

    def list_actions(self):
        with self.locked():
            return self.load()["actions"]

    def validate(self, action):
        action = dict(action)
        if not isinstance(action.get("name"), str) or not action["name"].strip():
            raise ShortcutError("Escribe un nombre para la acción.")
        action["name"] = action["name"].strip()
        mods = action.get("modifiers", [])
        if not isinstance(mods, list) or any(m not in MODIFIERS for m in mods) or not mods:
            raise ShortcutError("Utiliza Ctrl, Alt, Shift o Super en la combinación.")
        action["modifiers"] = [m for m in MODIFIERS if m in mods]
        action["key"] = canonical_key(action.get("key"))
        if action["key"] in ("Control_L", "Control_R", "Alt_L", "Alt_R", "Shift_L", "Shift_R", "Super_L", "Super_R", "Meta_L", "Meta_R", "ISO_Level3_Shift"):
            raise ShortcutError("Añade una tecla a los modificadores.")
        kind = action.get("type")
        if kind not in ("text", "command") or not isinstance(action.get(kind), str) or not action[kind]:
            raise ShortcutError("Escribe el texto o el comando de la acción.")
        if "\0" in action[kind] or len(action[kind].encode("utf-8")) > MAX_TEXT_BYTES:
            raise ShortcutError("El contenido contiene caracteres no admitidos o supera 1 MiB.")
        if "id" in action and (not isinstance(action["id"], str) or not re.fullmatch(r'[0-9a-f]{32}', action["id"])):
            raise ShortcutError("El identificador de la acción no es válido.")
        return {k: action[k] for k in ("id", "name", "key", "modifiers", "type", kind) if k in action}

    @staticmethod
    def command(launcher, identifier):
        return shlex.quote(launcher) + " --run " + identifier

    def save_action(self, action):
        action = self.validate(action)
        with self.locked():
            state = self.load()
            if "id" in action and not any(a["id"] == action["id"] for a in state["actions"]):
                raise ShortcutError("La acción ya no existe; vuelve a abrirla.")
            action.setdefault("id", uuid.uuid4().hex)
            actions = [a for a in state["actions"] if a["id"] != action["id"]]
            actions.append(action)
            self.commit(state, actions)
        return action["id"]

    def delete_action(self, identifier):
        with self.locked():
            state = self.load()
            actions = [a for a in state["actions"] if a["id"] != identifier]
            self.commit(state, actions)

    def commit(self, state, actions):
        original = read_file(self.custom_path, "{}\n")
        entries, tail = map_entries(original)
        old_launcher = state.get("launcher", self.launcher)
        owned = {self.command(old_launcher, a["id"]) for a in state["actions"]}
        foreign = [e for e in entries if binding(e)[1] not in owned]
        used = {binding(e)[0] for e in foreign}
        for action in actions:
            identity = (frozenset(action["modifiers"]), action["key"])
            if identity in used:
                raise ShortcutError("Esa combinación ya está asignada. Cambia o elimina primero el otro atajo en Ajustes de COSMIC.")
            used.add(identity)
        rendered = list(foreign)
        for action in actions:
            rendered.append("\n    (modifiers: [" + ", ".join(action["modifiers"]) + "], key: "
                            + ron_quote(action["key"]) + ", description: Some("
                            + ron_quote(action["name"]) + ")): Spawn("
                            + ron_quote(self.command(self.launcher, action["id"])) + ")")
        custom = "{" + "".join(e + "," for e in rendered) + tail + "\n}\n"
        new_state = json.dumps({"version": 1, "launcher": self.launcher, "actions": actions}, ensure_ascii=False, indent=2) + "\n"
        if max(len(new_state.encode("utf-8")), len(custom.encode("utf-8"))) > MAX_CONFIG_BYTES:
            raise ShortcutError("Las acciones guardadas superan el límite total de 4 MiB.")
        old_state = read_file(self.state_path, None)
        # Keep a recoverable copy before the first change, including foreign entries.
        backup = self.custom_path.with_name("custom.before-xappiens-shortcuts")
        if not backup.exists():
            atomic_write(backup, original)
        atomic_write(self.state_path, new_state)
        try:
            # Refuse to overwrite a simultaneous edit by COSMIC Settings.
            if read_file(self.custom_path, "{}\n") != original:
                raise ShortcutError("Los atajos cambiaron en otra aplicación; vuelve a guardar.")
            atomic_write(self.custom_path, custom)
        except BaseException:
            if old_state is None:
                self.state_path.unlink(missing_ok=True)
            else:
                atomic_write(self.state_path, old_state)
            raise

    def run_action(self, identifier):
        action = next((a for a in self.list_actions() if a["id"] == identifier), None)
        if action is None:
            raise ShortcutError("La acción ya no existe.")
        if os.getuid() == 0:
            raise ShortcutError("Los atajos deben ejecutarse en la sesión del usuario.")
        if action["type"] == "command":
            # Commands are explicit actions; stored text never takes this route.
            subprocess.Popen(["/bin/sh", "-c", action["command"]], start_new_session=True,
                             stdin=subprocess.DEVNULL)
            return
        if not os.environ.get("WAYLAND_DISPLAY"):
            raise ShortcutError("El pegado necesita una sesión Wayland.")
        runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
        fd = os.open(runtime / "xappiens-shortcuts-paste.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return
            data = action["text"].encode("utf-8")
            # Both selections: COSMIC Terminal uses PRIMARY for Shift+Insert.
            for selection in ([], ["--primary"]):
                try:
                    result = subprocess.run(["wl-copy", *selection, "--type", "text/plain;charset=utf-8"],
                                            input=data, stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL, timeout=3)
                except (OSError, subprocess.TimeoutExpired) as error:
                    raise ShortcutError("No se pudo preparar el texto para pegar.") from error
                if result.returncode:
                    raise ShortcutError("No se pudo preparar el texto para pegar.")
            time.sleep(0.25)
            try:
                result = subprocess.run([str(Path(__file__).with_name("paste-key"))],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
            except (OSError, subprocess.TimeoutExpired) as error:
                raise ShortcutError("Texto copiado. Pulsa Ctrl + V para pegarlo.") from error
            if result.returncode:
                raise ShortcutError("Texto copiado. Pulsa Ctrl + V para pegarlo.")
