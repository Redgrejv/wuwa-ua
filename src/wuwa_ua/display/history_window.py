from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402

from wuwa_ua.history import HistoryRecord, read_history  # noqa: E402

STYLE = b"""
window { background-color: #101014; }
label.translation { color: #f2f2f5; font-size: 19px; }
label.source { color: #7a7a86; font-size: 14px; font-style: italic; }
label.untranslated { color: #d8a657; }
label.empty { color: #6f6f7a; font-size: 16px; }
"""

POLL_SECONDS = 2


class HistoryWindow:
    def __init__(self, path: Path, limit: int = 500) -> None:
        self._path = path
        self._limit = limit
        self._app = Gtk.Application(application_id="io.github.wuwaua.history")
        self._app.connect("activate", self._on_activate)
        self._box: Gtk.Box | None = None
        self._scroller: Gtk.ScrolledWindow | None = None
        self._shown = 0

    def run(self) -> None:
        self._app.run(None)

    def _on_activate(self, app: Gtk.Application) -> None:
        window = Gtk.ApplicationWindow(application=app, title="wuwa-ua: історія діалогу")
        window.set_default_size(900, 700)

        provider = Gtk.CssProvider()
        provider.load_from_data(STYLE)
        Gtk.StyleContext.add_provider_for_display(
            window.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self._box.set_margin_top(18)
        self._box.set_margin_bottom(18)
        self._box.set_margin_start(22)
        self._box.set_margin_end(22)

        self._scroller = Gtk.ScrolledWindow(vexpand=True)
        self._scroller.set_child(self._box)
        window.set_child(self._scroller)
        window.present()

        self._refresh()
        GLib.timeout_add_seconds(POLL_SECONDS, self._refresh)

    def _refresh(self) -> bool:
        if self._box is None:
            return True
        records = read_history(self._path, self._limit)
        if not records:
            if self._shown == 0:
                self._append_placeholder()
                self._shown = -1
            return True
        if self._shown == -1:
            self._clear_box()
            self._shown = 0
        if len(records) == self._shown:
            return True
        for record in records[self._shown :]:
            self._append(record)
        self._shown = len(records)
        self._scroll_to_end()
        return True

    def _clear_box(self) -> None:
        if self._box is None:
            return
        child = self._box.get_first_child()
        while child is not None:
            self._box.remove(child)
            child = self._box.get_first_child()

    def _append_placeholder(self) -> None:
        if self._box is None:
            return
        label = Gtk.Label(label="Ще нічого не перекладено.", xalign=0.0)
        label.set_css_classes(["empty"])
        self._box.append(label)

    def _append(self, record: HistoryRecord) -> None:
        if self._box is None:
            return
        entry = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        translation = Gtk.Label(label=record.translation, wrap=True, xalign=0.0)
        translation.set_css_classes(
            ["translation"] if record.translated else ["translation", "untranslated"]
        )
        source = Gtk.Label(label=record.source, wrap=True, xalign=0.0)
        source.set_css_classes(["source"])

        entry.append(translation)
        entry.append(source)
        self._box.append(entry)

    def _scroll_to_end(self) -> None:
        if self._scroller is None:
            return
        adjustment = self._scroller.get_vadjustment()
        GLib.idle_add(
            adjustment.set_value, adjustment.get_upper() - adjustment.get_page_size()
        )
