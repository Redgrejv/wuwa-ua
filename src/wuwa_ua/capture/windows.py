from __future__ import annotations

import time
from collections.abc import Iterator

import numpy as np

from wuwa_ua.types import Frame

CAPTURE_FPS = 8.0


class CaptureError(Exception):
    pass


class MonitorCapture:
    def __init__(self, monitor_index: int = 1, fps: float = CAPTURE_FPS) -> None:
        self._monitor_index = monitor_index
        self._fps = fps
        self._grab = None
        self._region: dict[str, int] | None = None
        self.restore_token = ""

    def start(self) -> None:
        try:
            import mss
        except ImportError as exc:
            raise CaptureError("не встановлено mss — `pip install mss`") from exc

        self._grab = mss.mss()
        monitors = self._grab.monitors
        if self._monitor_index >= len(monitors):
            raise CaptureError(
                f"монітор {self._monitor_index} не знайдено, доступно {len(monitors) - 1}"
            )
        self._region = monitors[self._monitor_index]

    def frames(self) -> Iterator[Frame]:
        if self._grab is None or self._region is None:
            raise CaptureError("захоплення не запущено")
        interval = 1.0 / self._fps
        while True:
            started = time.monotonic()
            shot = self._grab.grab(self._region)
            image = np.asarray(shot)[:, :, :3].copy()
            yield Frame(image=image, timestamp=time.monotonic())
            elapsed = time.monotonic() - started
            if elapsed < interval:
                time.sleep(interval - elapsed)

    def stop(self) -> None:
        if self._grab is not None:
            self._grab.close()
            self._grab = None
        self._region = None
