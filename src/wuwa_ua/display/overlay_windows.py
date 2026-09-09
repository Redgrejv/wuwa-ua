from __future__ import annotations

import ctypes
import queue
from typing import Any

import numpy as np

from wuwa_ua.display.backdrop import backdrop
from wuwa_ua.types import Region, SubtitleLine

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WDA_EXCLUDEFROMCAPTURE = 0x00000011

OUTLINE_OFFSETS = ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, -2), (-2, 2), (2, 2))
FONT = ("Segoe UI Semibold", 17)
TEXT_COLOUR = "#ffffff"
UNTRANSLATED_COLOUR = "#f0c674"
OUTLINE_COLOUR = "#000000"
POLL_MS = 60


def make_click_through(window_id: int) -> None:
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    user32.GetWindowLongW.restype = wintypes.LONG
    style = user32.GetWindowLongW(window_id, GWL_EXSTYLE)
    style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
    user32.SetWindowLongW(window_id, GWL_EXSTYLE, style)


def hide_from_capture(window_id: int) -> bool:
    user32 = ctypes.windll.user32
    return bool(user32.SetWindowDisplayAffinity(window_id, WDA_EXCLUDEFROMCAPTURE))


def plate_rect(
    region: Region, monitor_width: int, monitor_height: int, top: float = 0.0
) -> tuple[int, int, int, int]:
    left, band_top, right, bottom = region.pixels(monitor_width, monitor_height)
    if top:
        band_top = min(band_top, int(top * monitor_height))
    return left, band_top, right - left, bottom - band_top


class WindowsOverlayDisplay:
    def __init__(
        self,
        region: Region,
        plate_top: float = 0.0,
        monitor_offset: tuple[int, int] = (0, 0),
    ) -> None:
        self._region = region
        self._plate_top = plate_top
        self._monitor_offset = monitor_offset
        self._queue: queue.Queue[tuple[str, SubtitleLine | None, np.ndarray | None]] = queue.Queue()
        self._root: Any = None
        self._canvas: Any = None
        self._photo = None
        self._width = 0
        self._height = 0

    def show(self, line: SubtitleLine, background: np.ndarray | None = None) -> None:
        self._queue.put(("show", line, background))

    def pending(self, background: np.ndarray | None = None) -> None:
        self._queue.put(("pending", None, background))

    def clear(self) -> None:
        self._queue.put(("clear", None, None))

    def run(self) -> None:
        import tkinter as tk

        root = tk.Tk()
        self._root = root
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg="black")

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        left, top, width, height = plate_rect(
            self._region, screen_width, screen_height, self._plate_top
        )
        offset_x, offset_y = self._monitor_offset
        self._width, self._height = width, height
        root.geometry(f"{width}x{height}+{left + offset_x}+{top + offset_y}")

        self._canvas = tk.Canvas(
            root, width=width, height=height, highlightthickness=0, bg="black"
        )
        self._canvas.pack()

        root.update_idletasks()
        window_id = root.winfo_id()
        make_click_through(window_id)
        hide_from_capture(window_id)
        root.withdraw()

        root.after(POLL_MS, self._drain)
        root.mainloop()

    def _drain(self) -> None:
        root = self._root
        if root is None:
            return
        try:
            while True:
                action, line, background = self._queue.get_nowait()
                if action == "clear":
                    root.withdraw()
                elif action == "pending":
                    self._render(background, "…", TEXT_COLOUR)
                    root.deiconify()
                elif line is not None:
                    colour = TEXT_COLOUR if line.translated else UNTRANSLATED_COLOUR
                    if line.translation:
                        self._render(background, line.translation, colour)
                        root.deiconify()
                    else:
                        root.withdraw()
        except queue.Empty:
            pass
        root.after(POLL_MS, self._drain)

    def _render(self, background: np.ndarray | None, text: str, colour: str) -> None:
        canvas = self._canvas
        if canvas is None:
            return
        canvas.delete("all")

        if background is not None:
            from PIL import Image, ImageTk

            blurred = backdrop(background)[:, :, ::-1]
            image = Image.fromarray(blurred).resize((self._width, self._height))
            self._photo = ImageTk.PhotoImage(image)
            canvas.create_image(0, 0, anchor="nw", image=self._photo)
        else:
            canvas.create_rectangle(
                0, 0, self._width, self._height, fill="#08080c", outline=""
            )

        centre_x = self._width // 2
        centre_y = self._height // 2
        wrap = self._width - 40
        for dx, dy in OUTLINE_OFFSETS:
            canvas.create_text(
                centre_x + dx,
                centre_y + dy,
                text=text,
                fill=OUTLINE_COLOUR,
                font=FONT,
                width=wrap,
                justify="center",
            )
        canvas.create_text(
            centre_x, centre_y, text=text, fill=colour, font=FONT, width=wrap, justify="center"
        )
