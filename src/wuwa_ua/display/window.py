from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402

from wuwa_ua.types import SubtitleLine  # noqa: E402

STYLE = b"""
window { background-color: #101014; }
label.current { color: #f2f2f5; font-size: 26px; font-weight: 600; }
label.source { color: #8a8a96; font-size: 15px; font-style: italic; }
label.history { color: #6f6f7a; font-size: 15px; }
label.untranslated { color: #d8a657; }
"""

EMPTY_LINE = SubtitleLine(source="", translation="", translated=True, timestamp=0.0)


class WindowDisplay:
    def __init__(self, monitor: str, history_size: int = 8) -> None:
        self._monitor = monitor
        self._history_size = history_size
        self._app = Gtk.Application(application_id="io.github.wuwaua")
        self._app.connect("activate", self._on_activate)
        self._current: Gtk.Label | None = None
        self._source: Gtk.Label | None = None
        self._history_box: Gtk.Box | None = None
        self._history: list[str] = []
        self._pending: SubtitleLine | None = None

    def run(self) -> None:
        self._app.run(None)

    def show(self, line: SubtitleLine, background: object | None = None) -> None:
        GLib.idle_add(self._apply, line)

    def pending(self, background: object | None = None) -> None:
        return None

    def clear(self) -> None:
        GLib.idle_add(self._apply, EMPTY_LINE)

    def _apply(self, line: SubtitleLine) -> bool:
        if self._current is None:
            self._pending = line
            return False
        previous = self._current.get_label()
        if previous:
            self._push_history(previous)
        self._current.set_label(line.translation)
        if self._source is not None:
            self._source.set_label(line.source)
        self._current.set_css_classes(
            ["current"] if line.translated else ["current", "untranslated"]
        )
        return False

    def _push_history(self, text: str) -> None:
        if self._history_box is None:
            return
        self._history.append(text)
        while len(self._history) > self._history_size:
            self._history.pop(0)
        child = self._history_box.get_first_child()
        while child is not None:
            self._history_box.remove(child)
            child = self._history_box.get_first_child()
        for entry in reversed(self._history):
            label = Gtk.Label(label=entry, wrap=True, xalign=0.0)
            label.set_css_classes(["history"])
            self._history_box.append(label)

    def _on_activate(self, app: Gtk.Application) -> None:
        self._current = Gtk.Label(label="", wrap=True, xalign=0.0)
        self._source = Gtk.Label(label="", wrap=True, xalign=0.0)
        self._history_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        provider = Gtk.CssProvider()
        provider.load_from_data(STYLE)
        window = Gtk.ApplicationWindow(application=app, title="wuwa-ua")
        window.set_default_size(760, 520)
        Gtk.StyleContext.add_provider_for_display(
            window.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self._current.set_css_classes(["current"])
        self._source.set_css_classes(["source"])

        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        layout.set_margin_top(18)
        layout.set_margin_bottom(18)
        layout.set_margin_start(20)
        layout.set_margin_end(20)
        layout.append(self._current)
        layout.append(self._source)
        layout.append(Gtk.Separator())
        scroller = Gtk.ScrolledWindow(vexpand=True)
        scroller.set_child(self._history_box)
        layout.append(scroller)
        window.set_child(layout)
        window.present()

        if self._pending is not None:
            pending, self._pending = self._pending, None
            self._apply(pending)
