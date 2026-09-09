from __future__ import annotations

import threading
import time
from collections.abc import Callable, Sequence
from typing import Any

GRAB_MODIFIERS = (0, 1 << 1, 1 << 4, (1 << 1) | (1 << 4))
RETRY_SECONDS = 5.0
DEBOUNCE_SECONDS = 0.3


def should_fire(now: float, last: float | None, debounce: float = DEBOUNCE_SECONDS) -> bool:
    return last is None or now - last >= debounce


def matches_window(name: str | None, wm_class: Sequence[str] | None, needle: str) -> bool:
    if not needle:
        return False
    target = needle.casefold()
    if name and target in name.casefold():
        return True
    return bool(wm_class) and any(target in str(part).casefold() for part in wm_class)


def find_windows(root: Any, needle: str) -> list[Any]:
    found: list[Any] = []
    stack = [root]
    while stack:
        window = stack.pop()
        try:
            name = window.get_wm_name()
            wm_class = window.get_wm_class()
        except Exception:
            continue
        if matches_window(name, wm_class, needle):
            found.append(window)
        try:
            stack.extend(window.query_tree().children)
        except Exception:
            continue
    return found


class HotkeyListener:
    def __init__(self, window_match: str, bindings: dict[str, Callable[[], None]]) -> None:
        self._window_match = window_match
        self._bindings = {key: callback for key, callback in bindings.items() if key}
        self._running = False
        self._thread: threading.Thread | None = None

    @property
    def keys(self) -> list[str]:
        return list(self._bindings)

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _run(self) -> None:
        from Xlib import X, XK, display

        connection = display.Display()
        codes: dict[int, Callable[[], None]] = {}
        for key, callback in self._bindings.items():
            keycode = connection.keysym_to_keycode(XK.string_to_keysym(key))
            if keycode:
                codes[keycode] = callback
        if not codes:
            return

        windows: list[Any] = []
        while self._running and not windows:
            windows = find_windows(connection.screen().root, self._window_match)
            if not windows:
                connection.sync()
                threading.Event().wait(RETRY_SECONDS)

        if not windows:
            return

        for window in windows:
            for keycode in codes:
                for modifiers in GRAB_MODIFIERS:
                    try:
                        window.grab_key(keycode, modifiers, False, X.GrabModeAsync, X.GrabModeAsync)
                    except Exception:
                        continue
        connection.sync()

        last_fired: dict[int, float] = {}
        while self._running:
            if connection.pending_events() == 0:
                threading.Event().wait(0.05)
                continue
            event = connection.next_event()
            if event.type != X.KeyPress or event.detail not in codes:
                continue
            now = time.monotonic()
            if not should_fire(now, last_fired.get(event.detail)):
                continue
            last_fired[event.detail] = now
            codes[event.detail]()
