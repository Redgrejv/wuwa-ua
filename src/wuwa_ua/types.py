from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Region:
    monitor: str
    x: float
    y: float
    width: float
    height: float

    def pixels(self, frame_width: int, frame_height: int) -> tuple[int, int, int, int]:
        left = int(self.x * frame_width)
        top = int(self.y * frame_height)
        right = int((self.x + self.width) * frame_width)
        bottom = int((self.y + self.height) * frame_height)
        return left, top, right, bottom


@dataclass(frozen=True)
class Frame:
    image: np.ndarray
    timestamp: float


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: float


@dataclass(frozen=True)
class SubtitleLine:
    source: str
    translation: str
    translated: bool
    timestamp: float
