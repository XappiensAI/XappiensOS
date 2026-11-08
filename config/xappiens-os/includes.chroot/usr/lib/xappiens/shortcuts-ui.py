#!/usr/bin/python3
"""Native editor for the user's XappiensOS keyboard actions."""

import sys

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, Gtk

from xappiens_shortcuts import Manager, ShortcutError


MODIFIERS = ("Ctrl", "Alt", "Shift", "Super")
MODIFIER_KEYS = {
    "Control_L", "Control_R", "Alt_L", "Alt_R", "Shift_L", "Shift_R",
    "Super_L", "Super_R", "Meta_L", "Meta_R", "ISO_Level3_Shift",
    "Caps_Lock", "Num_Lock",
}


def shortcut_label(action):
    key = action.get("key", "")
    value = Gdk.keyval_from_name(key)
    label = key
    if value:
        character = Gdk.keyval_to_unicode(value)
        if character and chr(character).isprintable() and not chr(character).isspace():
            label = chr(character).upper()
        else:
            label = {"space": "Espacio", "Return": "Intro", "Escape": "Esc",
                     "dead_acute": "´", "dead_diaeresis": "¨"}.get(key, key)
    return " + ".join([*(m for m in MODIFIERS if m in action.get("modifiers", [])), label])


def shortcut_expression(action):
    """Keep named keys (including keypad keys) lossless in the editable field."""
    return " + ".join([*(m for m in MODIFIERS if m in action.get("modifiers", [])), action.get("key", "")])


def parse_shortcut(text):
    """Accept a readable chord as well as XKB names, without registering it."""
    parts = [part.strip() for part in text.strip().split("+")]
    # A final literal '+' can be entered as Ctrl++ or Ctrl + +.
    if len(parts) >= 2 and parts[-2:] == ["", ""]:
        parts = [*parts[:-2], "plus"]
    if not parts or not parts[-1] or any(not part for part in parts):
        raise ShortcutError("Introduce una combinación, por ejemplo Ctrl+Alt+'.")
    aliases = {
        "ctrl": "Ctrl", "control": "Ctrl", "alt": "Alt",
        "shift": "Shift", "mayús": "Shift", "mayus": "Shift",
        "super": "Super", "win": "Super", "windows": "Super",
    }
    modifiers = []
    for part in parts[:-1]:
        modifier = aliases.get(part.casefold())
        if not modifier or modifier in modifiers:
            raise ShortcutError("Usa Ctrl, Alt, Shift o Super, seguidos de una tecla.")
        modifiers.append(modifier)
    key_text = parts[-1]
    names = {"intro": "Return", "enter": "Return", "esc": "Escape", "espacio": "space",
             "´": "dead_acute", "¨": "dead_diaeresis"}
    key_text = names.get(key_text.casefold(), key_text)
    value = Gdk.unicode_to_keyval(ord(key_text)) if len(key_text) == 1 else Gdk.keyval_from_name(key_text)
    key = Gdk.keyval_name(Gdk.keyval_to_lower(value)) if value and value != Gdk.KEY_VoidSymbol else None
    if not key or key == "VoidSymbol" or key in MODIFIER_KEYS:
        raise ShortcutError("No se reconoce la tecla. Puedes escribir ´, ', F9, Return o apostrophe.")
    if key == "ISO_Left_Tab":
        key = "Tab"
    return {"key": key, "modifiers": [name for name in MODIFIERS if name in modifiers]}


def show_error(parent, message):
    dialog = Gtk.MessageDialog(
        transient_for=parent, modal=True, message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.CLOSE, text="No se pudo completar la acción",
    )
    dialog.format_secondary_text(message)
    dialog.run()
    dialog.destroy()


class ShortcutCapture(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="Asignar combinación", transient_for=parent, modal=True)
        self.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        self.set_default_size(390, 150)
        self.action = None
        box = self.get_content_area()
        box.set_border_width(24)
        box.set_spacing(12)
        label = Gtk.Label(label="Pulsa la combinación de teclas que quieras usar.")
        label.set_line_wrap(True)
        box.add(label)
        hint = Gtk.Label(label="Por ejemplo: Ctrl + Alt + '")
        hint.get_style_context().add_class("dim-label")
        box.add(hint)
        self.connect("key-press-event", self.capture)
        self.show_all()

    def capture(self, _widget, event):
        keyval = event.keyval
        if getattr(event, "hardware_keycode", 0):
            # COSMIC binds the unmodified keysym and stores Shift separately.
            # With ES layout, Shift+' produces '?' but the binding key is '.
            keymap = Gdk.Keymap.get_for_display(self.get_display())
            if keymap is not None:
                translated = keymap.translate_keyboard_state(
                    event.hardware_keycode, Gdk.ModifierType(0), event.group,
                )
                if translated[0]:
                    keyval = translated[1]
        key = Gdk.keyval_name(Gdk.keyval_to_lower(keyval))
        if not key or key in MODIFIER_KEYS:
            return True
        state = event.state
        modifiers = []
        for name, mask in (
            ("Ctrl", Gdk.ModifierType.CONTROL_MASK),
            ("Alt", Gdk.ModifierType.MOD1_MASK),
            ("Shift", Gdk.ModifierType.SHIFT_MASK),
            ("Super", Gdk.ModifierType.SUPER_MASK | Gdk.ModifierType.MOD4_MASK),
        ):
            if state & mask:
                modifiers.append(name)
        if key == "Escape" and not modifiers:
            self.response(Gtk.ResponseType.CANCEL)
            return True
        if key == "ISO_Left_Tab":
            key = "Tab"
        self.action = {"key": key, "modifiers": modifiers}
        self.response(Gtk.ResponseType.OK)
        return True


class ActionEditor(Gtk.Dialog):
    def __init__(self, parent, action=None):
        super().__init__(
            title="Editar atajo" if action else "Añadir atajo",
            transient_for=parent, modal=True,
        )
        self.action = dict(action or {})
        self.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        save = self.add_button("Guardar", Gtk.ResponseType.OK)
        save.get_style_context().add_class("suggested-action")
        self.set_default_size(520, 410)
        box = self.get_content_area()
        box.set_border_width(24)
        box.set_spacing(12)

        self.name = Gtk.Entry(text=self.action.get("name", ""))
        self.name.set_placeholder_text("Por ejemplo: Mi firma")
        self.add_field(box, "Nombre", self.name)
        self.shortcut = Gtk.Entry(
            text=shortcut_expression(self.action) if self.action.get("key") else "",
        )
        self.shortcut.set_placeholder_text("Ctrl+Alt+'")
        self.capture_button = Gtk.Button(label="Capturar…")
        self.capture_button.connect("clicked", self.choose_shortcut)
        shortcut_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        shortcut_box.pack_start(self.shortcut, True, True, 0)
        shortcut_box.pack_start(self.capture_button, False, False, 0)
        self.add_field(box, "Combinación de teclas", shortcut_box)
        shortcut_hint = Gtk.Label(
            label="Puedes escribirla directamente si la captura no la detecta. En teclado español, ´ y ' son teclas distintas.", xalign=0,
        )
        shortcut_hint.set_line_wrap(True)
        shortcut_hint.get_style_context().add_class("dim-label")
        box.pack_start(shortcut_hint, False, False, 0)
        self.kind = Gtk.ComboBoxText()
        self.kind.append("text", "Pegar texto")
        self.kind.append("command", "Ejecutar un comando")
        self.kind.set_active_id(self.action.get("type", "text"))
        self.add_field(box, "Acción", self.kind)

        self.stack = Gtk.Stack()
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        text_box.add(Gtk.Label(label="Texto que se pegará", xalign=0))
        self.text = Gtk.TextView()
        self.text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text.set_left_margin(8)
        self.text.set_right_margin(8)
        self.text.set_top_margin(8)
        self.text.set_bottom_margin(8)
        self.text.get_buffer().set_text(self.action.get("text", ""))
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(120)
        scroll.set_shadow_type(Gtk.ShadowType.IN)
        scroll.add(self.text)
        text_box.pack_start(scroll, True, True, 0)
        note = Gtk.Label(label="Se pegará tal como lo escribas, incluidos los saltos de línea.", xalign=0)
        note.set_line_wrap(True)
        note.get_style_context().add_class("dim-label")
        text_box.add(note)
        self.stack.add_named(text_box, "text")
        self.command = Gtk.Entry(text=self.action.get("command", ""))
        self.command.set_placeholder_text("Por ejemplo: cosmic-term")
        command_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        command_box.add(Gtk.Label(label="Aplicación o comando", xalign=0))
        command_box.add(self.command)
        self.stack.add_named(command_box, "command")
        self.stack.set_visible_child_name(self.kind.get_active_id())
        self.kind.connect("changed", lambda combo: self.stack.set_visible_child_name(combo.get_active_id()))
        box.pack_start(self.stack, True, True, 0)
        self.show_all()
        self.name.grab_focus()

    @staticmethod
    def add_field(box, label, widget):
        group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        group.add(Gtk.Label(label=label, xalign=0))
        group.add(widget)
        box.pack_start(group, False, False, 0)

    def choose_shortcut(self, _button):
        capture = ShortcutCapture(self)
        if capture.run() == Gtk.ResponseType.OK:
            self.action.update(capture.action)
            self.shortcut.set_text(shortcut_expression(self.action))
        capture.destroy()

    def get_action(self):
        action = {key: self.action[key] for key in ("id", "key", "modifiers") if key in self.action}
        action.update(parse_shortcut(self.shortcut.get_text()))
        action.update(name=self.name.get_text().strip(), type=self.kind.get_active_id())
        if action["type"] == "text":
            buffer = self.text.get_buffer()
            action["text"] = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
        else:
            action["command"] = self.command.get_text().strip()
        return action


class ShortcutsApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.xappiens.Shortcuts", flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None
        self.manager = None

    def do_activate(self):
        if self.window:
            self.window.present()
            return
        self.window = Gtk.ApplicationWindow(application=self)
        self.window.set_default_size(640, 450)
        self.window.set_title("Atajos personalizados")
        header = Gtk.HeaderBar(title="Atajos personalizados", show_close_button=True)
        add = Gtk.Button.new_from_icon_name("list-add-symbolic", Gtk.IconSize.BUTTON)
        add.set_tooltip_text("Añadir atajo")
        add.connect("clicked", lambda _button: self.edit_action())
        header.pack_end(add)
        self.window.set_titlebar(header)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_border_width(24)
        intro = Gtk.Label(
            label="Elige una combinación para pegar un texto o abrir una aplicación.", xalign=0,
        )
        intro.set_line_wrap(True)
        box.pack_start(intro, False, False, 0)
        self.rows = Gtk.ListBox()
        self.rows.set_selection_mode(Gtk.SelectionMode.NONE)
        self.rows.connect("row-activated", lambda _list, row: self.edit_action(row.action))
        empty = Gtk.Label(label="Todavía no has creado ningún atajo. Pulsa + para añadir uno.")
        empty.set_line_wrap(True)
        empty.set_margin_top(40)
        empty.set_margin_bottom(40)
        self.rows.set_placeholder(empty)
        empty.show()
        scroll = Gtk.ScrolledWindow()
        scroll.set_shadow_type(Gtk.ShadowType.IN)
        scroll.add(self.rows)
        box.pack_start(scroll, True, True, 0)
        self.window.add(box)
        self.window.show_all()
        try:
            self.manager = Manager()
            self.refresh()
        except (ShortcutError, OSError) as error:
            show_error(self.window, str(error))

    def refresh(self):
        actions = self.manager.list_actions()
        for child in self.rows.get_children():
            self.rows.remove(child)
        for action in actions:
            row = Gtk.ListBoxRow()
            row.action = action
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
            box.set_border_width(12)
            labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            title = Gtk.Label(label=action["name"], xalign=0)
            title.set_ellipsize(3)  # Pango.EllipsizeMode.END
            labels.add(title)
            subtitle = Gtk.Label(
                label=shortcut_label(action) + "  ·  " + (
                    "Pegar texto" if action["type"] == "text" else "Ejecutar comando"
                ), xalign=0,
            )
            subtitle.get_style_context().add_class("dim-label")
            subtitle.set_ellipsize(3)
            labels.add(subtitle)
            box.pack_start(labels, True, True, 0)
            edit = Gtk.Button.new_from_icon_name("document-edit-symbolic", Gtk.IconSize.BUTTON)
            edit.set_tooltip_text("Editar atajo")
            edit.connect("clicked", lambda _button, item=action: self.edit_action(item))
            box.pack_start(edit, False, False, 0)
            delete = Gtk.Button.new_from_icon_name("user-trash-symbolic", Gtk.IconSize.BUTTON)
            delete.set_tooltip_text("Eliminar atajo")
            delete.connect("clicked", lambda _button, item=action: self.delete_action(item))
            box.pack_start(delete, False, False, 0)
            row.add(box)
            self.rows.add(row)
        self.rows.show_all()

    def edit_action(self, action=None):
        if self.manager is None:
            return
        dialog = ActionEditor(self.window, action)
        try:
            while dialog.run() == Gtk.ResponseType.OK:
                try:
                    self.manager.save_action(dialog.get_action())
                    self.refresh()
                    break
                except (ShortcutError, OSError) as error:
                    show_error(dialog, str(error))
        finally:
            dialog.destroy()

    def delete_action(self, action):
        try:
            self.manager.delete_action(action["id"])
            self.refresh()
        except (ShortcutError, OSError) as error:
            show_error(self.window, str(error))


def main():
    return ShortcutsApplication().run([sys.argv[0]])


if __name__ == "__main__":
    sys.exit(main())
