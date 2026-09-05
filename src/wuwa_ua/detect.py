from __future__ import annotations

import cv2
import numpy as np

SIGNATURE_WIDTH = 64


class ChangeDetector:
    def __init__(self, change_threshold: float = 3.0, stable_frames: int = 2) -> None:
        self._change_threshold = change_threshold
        self._stable_frames = max(1, stable_frames)
        self._emitted: np.ndarray | None = None
        self._pending: np.ndarray | None = None
        self._stable_count = 0

    def reset(self) -> None:
        self._emitted = None
        self._pending = None
        self._stable_count = 0

    def push(self, crop: np.ndarray) -> np.ndarray | None:
        signature = self._signature(crop)

        if self._emitted is not None and self._distance(signature, self._emitted) <= self._change_threshold:
            self._pending = None
            self._stable_count = 0
            return None

        if self._pending is None or self._distance(signature, self._pending) > self._change_threshold:
            self._pending = signature
            self._stable_count = 1
            return None

        self._stable_count += 1
        if self._stable_count < self._stable_frames:
            return None

        self._emitted = signature
        self._pending = None
        self._stable_count = 0
        return crop

    def _signature(self, crop: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        height = max(1, int(gray.shape[0] * SIGNATURE_WIDTH / gray.shape[1]))
        resized = cv2.resize(gray, (SIGNATURE_WIDTH, height), interpolation=cv2.INTER_AREA)
        return resized.astype(np.float32)

    def _distance(self, left: np.ndarray, right: np.ndarray) -> float:
        if left.shape != right.shape:
            return float("inf")
        return float(np.abs(left - right).mean())
