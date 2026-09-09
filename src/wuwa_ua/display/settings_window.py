from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402

from wuwa_ua.settings import (  # noqa: E402
    HOTKEY_FIELDS,
    SettingsError,
    is_supported_key,
    latin_fallback,
    read_hotkeys,
    write_hotkeys,
)

STYLE = b"""
window { background-color: #16161c; }
label.title { color: #f2f2f5; font-size: 20px; font-weight: 700; }
label.row { color: #d6d6dd; font-size: 15px; }
label.hint { color: #8a8a96; font-size: 13px; }
label.error { color: #e06c75; font-size: 13px; }
label.saved { color: #98c379; font-size: 13px; }
button.capturing { background: #3a3a48; }
"""

TITLES = {
    "key": "Сховати / показати переклад",
    "refresh_key": "Перекласти репліку наново",
    "history_key": "Відкрити історію діалогу",
}
CAPTURE_PROMPT = "натисни клавішу…"


def keysym_name(keyval: int) -> str:
    name = Gdk.keyval_name(keyval)
    if name is None:
        return ""
    if len(name) == 1 and name.isalnum():
        return name.lower()
    return name


class SettingsWindow:
    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path
        self._values = read_hotkeys(config_path)
        self._app = Gtk.Application(application_id="io.github.wuwaua.settings")
        self._app.connect("activate", self._on_activate)
        self._buttons: dict[str, Gtk.Button] = {}
        self._capturing: str | None = None
        self._status: Gtk.Label | None = None

    def run(self) -> None:
        self._app.run(None)

    def _on_activate(self, app: Gtk.Application) -> None:
        window = Gtk.ApplicationWindow(application=app, title="wuwa-ua: налаштування")
        window.set_default_size(560, 340)

        provider = Gtk.CssProvider()
        provider.load_from_data(STYLE)
        Gtk.StyleContext.add_provider_for_display(
            window.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        layout.set_margin_top(22)
        layout.set_margin_bottom(22)
        layout.set_margin_start(24)
        layout.set_margin_end(24)

        title = Gtk.Label(label="Гарячі клавіші", xalign=0.0)
        title.set_css_classes(["title"])
        layout.append(title)

        hint = Gtk.Label(
            label="Клавіші працюють лише коли активне вікно гри.\n"
            "Натисни кнопку й натисни потрібну клавішу. Backspace вимикає.",
            xalign=0.0,
            wrap=True,
        )
        hint.set_css_classes(["hint"])
        layout.append(hint)

        for field in HOTKEY_FIELDS:
            layout.append(self._make_row(field))

        self._status = Gtk.Label(label="", xalign=0.0)
        layout.append(self._status)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        buttons.set_halign(Gtk.Align.END)
        save = Gtk.Button(label="Зберегти")
        save.connect("clicked", self._on_save)
        close = Gtk.Button(label="Закрити")
        close.connect("clicked", lambda _button: window.close())
        buttons.append(close)
        buttons.append(save)
        layout.append(buttons)

        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._on_key)
        window.add_controller(controller)

        window.set_child(layout)
        window.present()

    def _make_row(self, field: str) -> Gtk.Box:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        label = Gtk.Label(label=TITLES[field], xalign=0.0, hexpand=True)
        label.set_css_classes(["row"])
        button = Gtk.Button(label=self._label_for(field))
        button.set_size_request(150, -1)
        button.connect("clicked", self._on_capture, field)
        self._buttons[field] = button
        row.append(label)
        row.append(button)
        return row

    def _label_for(self, field: str) -> str:
        return self._values.get(field) or "вимкнено"

    def _on_capture(self, button: Gtk.Button, field: str) -> None:
        self._capturing = field
        button.set_label(CAPTURE_PROMPT)
        button.set_css_classes(["capturing"])
        self._set_status("", "hint")

    def _on_key(self, _controller: Gtk.EventControllerKey, keyval: int, _code: int, _state) -> bool:
        field = self._capturing
        if field is None:
            return False

        name = keysym_name(keyval)
        if name in ("BackSpace", "Delete"):
            name = ""
        elif not is_supported_key(name):
            name = latin_fallback(name)
            if not name:
                self._set_status("цю клавішу призначити не можна", "error")
                self._finish_capture(field)
                return True

        self._values[field] = name
        self._finish_capture(field)
        return True

    def _finish_capture(self, field: str) -> None:
        self._capturing = None
        button = self._buttons[field]
        button.set_label(self._label_for(field))
        button.set_css_classes([])

    def _on_save(self, _button: Gtk.Button) -> None:
        try:
            write_hotkeys(self._config_path, self._values)
        except SettingsError as exc:
            self._set_status(str(exc), "error")
            return
        self._set_status("Збережено. Зміни підхопляться після перезапуску перекладу.", "saved")

    def _set_status(self, text: str, style: str) -> None:
        if self._status is None:
            return
        self._status.set_label(text)
        self._status.set_css_classes([style])
