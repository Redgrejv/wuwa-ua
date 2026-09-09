from __future__ import annotations

import cv2
import numpy as np

BLUR_SIGMA = 14.0
BLUR_DOWNSCALE = 4
DARKEN_FACTOR = 0.55


def blur(image: np.ndarray, sigma: float = BLUR_SIGMA) -> np.ndarray:
    height, width = image.shape[:2]
    small_height = max(1, height // BLUR_DOWNSCALE)
    small_width = max(1, width // BLUR_DOWNSCALE)
    small = cv2.resize(image, (small_width, small_height), interpolation=cv2.INTER_AREA)
    smoothed = cv2.GaussianBlur(small, (0, 0), sigma / BLUR_DOWNSCALE)
    return cv2.resize(smoothed, (width, height), interpolation=cv2.INTER_LINEAR)


def darken(image: np.ndarray, factor: float = DARKEN_FACTOR) -> np.ndarray:
    return np.clip(image.astype(np.float32) * factor, 0, 255).astype(np.uint8)


def backdrop(image: np.ndarray) -> np.ndarray:
    return darken(blur(image))
