from __future__ import annotations

import ctypes
import threading
import time
from collections.abc import Callable

from wuwa_ua.hotkey import should_fire

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
HC_ACTION = 0

VIRTUAL_KEYS = {
    "Page_Up": 0x21,
    "Page_Down": 0x22,
    "Home": 0x24,
    "End": 0x23,
    "Insert": 0x2D,
    "Delete": 0x2E,
    "F1": 0x70,
    "F2": 0x71,
    "F3": 0x72,
    "F4": 0x73,
    "F5": 0x74,
    "F6": 0x75,
    "F7": 0x76,
    "F8": 0x77,
    "F9": 0x78,
    "F10": 0x79,
    "F11": 0x7A,
    "F12": 0x7B,
}


def virtual_key(name: str) -> int | None:
    if name in VIRTUAL_KEYS:
        return VIRTUAL_KEYS[name]
    if len(name) == 1 and name.isalnum():
        return ord(name.upper())
    return None


def window_matches(title: str, needle: str) -> bool:
    if not needle:
        return False
    return needle.casefold() in title.casefold()


def foreground_title() -> str:
    user32 = ctypes.windll.user32
    handle = user32.GetForegroundWindow()
    if not handle:
        return ""
    length = user32.GetWindowTextLengthW(handle)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(handle, buffer, length + 1)
    return buffer.value


class WindowsHotkeyListener:
    def __init__(self, window_match: str, bindings: dict[str, Callable[[], None]]) -> None:
        self._window_match = window_match
        self._bindings = {key: callback for key, callback in bindings.items() if key}
        self._running = False
        self._thread: threading.Thread | None = None
        self._hook = None

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
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        codes: dict[int, Callable[[], None]] = {}
        for key, callback in self._bindings.items():
            code = virtual_key(key)
            if code is not None:
                codes[code] = callback
        if not codes:
            return

        last_fired: dict[int, float] = {}

        HOOKPROC = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
        )

        def callback(code: int, w_param: int, l_param: object) -> int:
            if code == HC_ACTION and w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
                vk = ctypes.cast(l_param, ctypes.POINTER(ctypes.c_ulong))[0]
                handler = codes.get(vk)
                if handler is not None and window_matches(foreground_title(), self._window_match):
                    now = time.monotonic()
                    if should_fire(now, last_fired.get(vk)):
                        last_fired[vk] = now
                        handler()
                    return 1
            return user32.CallNextHookEx(None, code, w_param, l_param)

        pointer = HOOKPROC(callback)
        self._hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, pointer, kernel32.GetModuleHandleW(None), 0
        )
        if not self._hook:
            return

        message = ctypes.create_string_buffer(64)
        while self._running:
            if not user32.PeekMessageW(message, None, 0, 0, 1):
                time.sleep(0.01)
        user32.UnhookWindowsHookEx(self._hook)
