from __future__ import annotations

import ctypes.util
from collections.abc import Mapping

import cairo
import gi
import numpy as np

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Pango  # noqa: E402
from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402

from wuwa_ua.display.backdrop import backdrop  # noqa: E402
from wuwa_ua.types import Region, SubtitleLine  # noqa: E402

OUTLINE = (
    "-1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000, "
    "0 -2px 2px #000, 0 2px 2px #000, -2px 0 2px #000, 2px 0 2px #000"
)
STYLE = f"""
window {{ background-color: transparent; }}
label.overlay {{
    color: #ffffff;
    font-size: 24px;
    font-weight: 700;
    padding: 8px 18px;
    text-shadow: {OUTLINE};
}}
label.untranslated {{ color: #f0c674; }}
""".encode()

EMPTY_LINE = SubtitleLine(source="", translation="", translated=True, timestamp=0.0)
DEFAULT_BOTTOM_MARGIN = 148
LAYER_SHELL_SONAME = "libgtk4-layer-shell.so"


def plate_geometry(
    region: Region,
    monitor_width: int,
    monitor_height: int,
    top: float | None = None,
) -> tuple[int, int, int, int]:
    left, band_top, right, bottom = region.pixels(monitor_width, monitor_height)
    if top is not None:
        band_top = min(band_top, int(top * monitor_height))
    return left, right - left, bottom - band_top, monitor_height - bottom


def find_layer_shell_library() -> str:
    return ctypes.util.find_library("gtk4-layer-shell") or LAYER_SHELL_SONAME


def needs_preload(env: Mapping[str, str], library: str) -> bool:
    return library not in [part for part in env.get("LD_PRELOAD", "").split(":") if part]


def preload_env(env: Mapping[str, str], library: str) -> dict[str, str]:
    updated = dict(env)
    parts = [part for part in updated.get("LD_PRELOAD", "").split(":") if part]
    if library not in parts:
        updated["LD_PRELOAD"] = ":".join([library, *parts])
    return updated


def texture_from_bgr(image: np.ndarray) -> Gdk.Texture:
    rgb = np.ascontiguousarray(image[:, :, ::-1])
    height, width = rgb.shape[:2]
    pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
        GLib.Bytes.new(rgb.tobytes()),
        GdkPixbuf.Colorspace.RGB,
        False,
        8,
        width,
        height,
        width * 3,
    )
    return Gdk.Texture.new_for_pixbuf(pixbuf)


class OverlayDisplay:
    def __init__(
        self,
        monitor: str,
        region: Region | None = None,
        plate_top: float = 0.0,
        bottom_margin: int = DEFAULT_BOTTOM_MARGIN,
    ) -> None:
        self._monitor = monitor
        self._region = region
        self._plate_top = plate_top or None
        self._bottom_margin = bottom_margin
        self._app = Gtk.Application(application_id="io.github.wuwaua.overlay")
        self._app.connect("activate", self._on_activate)
        self._label: Gtk.Label | None = None
        self._picture: Gtk.Picture | None = None
        self._spinner: Gtk.Spinner | None = None
        self._pending: SubtitleLine | None = None
        self._pending_background: np.ndarray | None = None

    def run(self) -> None:
        self._app.run(None)

    def show(self, line: SubtitleLine, background: np.ndarray | None = None) -> None:
        GLib.idle_add(self._apply, line, background)

    def pending(self, background: np.ndarray | None = None) -> None:
        GLib.idle_add(self._apply_pending, background)

    def clear(self) -> None:
        GLib.idle_add(self._apply, EMPTY_LINE, None)

    def _apply_pending(self, background: np.ndarray | None = None) -> bool:
        if self._label is None or self._spinner is None:
            return False
        if background is not None and self._picture is not None:
            self._picture.set_paintable(texture_from_bgr(backdrop(background)))
            self._picture.set_visible(True)
        self._label.set_visible(False)
        self._spinner.set_visible(True)
        self._spinner.start()
        return False

    def _apply(self, line: SubtitleLine, background: np.ndarray | None = None) -> bool:
        if self._label is None:
            self._pending = line
            self._pending_background = background
            return False

        visible = bool(line.translation)
        if self._spinner is not None:
            self._spinner.stop()
            self._spinner.set_visible(False)
        if background is not None and self._picture is not None:
            self._picture.set_paintable(texture_from_bgr(backdrop(background)))
        if self._picture is not None:
            self._picture.set_visible(visible and background is not None)

        self._label.set_label(line.translation)
        self._label.set_visible(visible)
        self._label.set_css_classes(
            ["overlay"] if line.translated else ["overlay", "untranslated"]
        )
        return False

    def _on_activate(self, app: Gtk.Application) -> None:
        self._label = Gtk.Label(label="", wrap=True, justify=Gtk.Justification.CENTER)
        self._picture = Gtk.Picture()
        self._picture.set_content_fit(Gtk.ContentFit.FILL)
        self._picture.set_visible(False)
        self._spinner = Gtk.Spinner()
        self._spinner.set_size_request(28, 28)
        self._spinner.set_halign(Gtk.Align.CENTER)
        self._spinner.set_valign(Gtk.Align.CENTER)
        self._spinner.set_visible(False)

        window = Gtk.ApplicationWindow(application=app)
        LayerShell.init_for_window(window)
        LayerShell.set_layer(window, LayerShell.Layer.OVERLAY)
        LayerShell.set_anchor(window, LayerShell.Edge.BOTTOM, True)
        LayerShell.set_keyboard_mode(window, LayerShell.KeyboardMode.NONE)

        margin = self._bottom_margin
        plate_size: tuple[int, int] | None = None
        for monitor in window.get_display().get_monitors():
            if monitor.get_connector() != self._monitor:
                continue
            LayerShell.set_monitor(window, monitor)
            if self._region is not None:
                geometry = monitor.get_geometry()
                left, width, height, margin = plate_geometry(
                    self._region, geometry.width, geometry.height, self._plate_top
                )
                LayerShell.set_anchor(window, LayerShell.Edge.LEFT, True)
                LayerShell.set_margin(window, LayerShell.Edge.LEFT, left)
                plate_size = (width, height)
                self._label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
                self._label.set_max_width_chars(1)
            break
        LayerShell.set_margin(window, LayerShell.Edge.BOTTOM, margin)

        provider = Gtk.CssProvider()
        provider.load_from_data(STYLE)
        Gtk.StyleContext.add_provider_for_display(
            window.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self._label.set_css_classes(["overlay"])
        self._label.set_visible(False)

        self._label.set_valign(Gtk.Align.CENTER)
        self._label.set_halign(Gtk.Align.FILL)
        self._picture.set_hexpand(True)
        self._picture.set_vexpand(True)

        stack = Gtk.Overlay()
        stack.set_child(self._picture)
        stack.add_overlay(self._label)
        stack.add_overlay(self._spinner)
        if plate_size is not None:
            stack.set_size_request(*plate_size)
        window.set_child(stack)
        window.present()

        surface = window.get_surface()
        if surface is not None:
            surface.set_input_region(cairo.Region())

        if self._pending is not None:
            pending, self._pending = self._pending, None
            background, self._pending_background = self._pending_background, None
            self._apply(pending, background)
