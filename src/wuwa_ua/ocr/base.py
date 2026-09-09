from __future__ import annotations

from typing import Protocol

import numpy as np

from wuwa_ua.types import OcrResult


class OcrBackend(Protocol):
    def recognize(self, image: np.ndarray) -> OcrResult: ...
