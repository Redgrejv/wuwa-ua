from __future__ import annotations

import numpy as np

from wuwa_ua.display.backdrop import blur, darken


def noisy(height: int = 60, width: int = 200) -> np.ndarray:
    rng = np.random.default_rng(7)
    return rng.integers(0, 255, size=(height, width, 3), dtype=np.uint8)


def test_blur_keeps_shape_and_dtype() -> None:
    image = noisy()

    result = blur(image)

    assert result.shape == image.shape
    assert result.dtype == np.uint8


def test_blur_smooths_the_image() -> None:
    image = noisy()

    assert float(blur(image).var()) < float(image.var())


def test_blur_handles_a_tiny_image() -> None:
    image = noisy(height=3, width=4)

    assert blur(image).shape == image.shape


def test_darken_reduces_brightness() -> None:
    image = np.full((10, 10, 3), 200, dtype=np.uint8)

    result = darken(image, 0.5)

    assert int(result.mean()) == 100


def test_darken_keeps_black_black() -> None:
    image = np.zeros((4, 4, 3), dtype=np.uint8)

    assert int(darken(image, 0.5).max()) == 0


def test_darken_without_change_is_identity() -> None:
    image = noisy(height=8, width=8)

    assert np.array_equal(darken(image, 1.0), image)
