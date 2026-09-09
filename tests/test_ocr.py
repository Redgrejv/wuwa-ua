from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from wuwa_ua.ocr.tesseract import TesseractOcr, preprocess_bright, preprocess_tophat

FIXTURES = Path(__file__).parent / "ocr_fixtures"
FIELD_FIXTURES = ["field-01", "field-02", "field-03", "field-04"]


def solid(colour: int, height: int = 40, width: int = 200) -> np.ndarray:
    return np.full((height, width, 3), colour, dtype=np.uint8)


@pytest.mark.parametrize("preprocess", [preprocess_bright, preprocess_tophat])
def test_preprocess_upscales_twice(preprocess) -> None:
    result = preprocess(solid(0))

    assert result.shape == (80, 400)


@pytest.mark.parametrize("preprocess", [preprocess_bright, preprocess_tophat])
def test_preprocess_returns_a_binary_image(preprocess) -> None:
    result = preprocess(solid(120))

    assert set(np.unique(result)).issubset({0, 255})


def test_bright_preprocess_inverts_text_to_dark_on_white() -> None:
    image = solid(0)
    image[10:30, 20:180] = 255

    result = preprocess_bright(image)

    assert int(result[0, 0]) == 255
    assert int(result[40, 100]) == 0


@pytest.mark.parametrize("name", FIELD_FIXTURES)
def test_reads_real_subtitles_verbatim(name: str) -> None:
    image = cv2.imread(str(FIXTURES / f"{name}.png"), cv2.IMREAD_COLOR)
    expected = (FIXTURES / f"{name}.txt").read_text(encoding="utf-8").strip()

    result = TesseractOcr().recognize(image)

    assert result.confidence >= 60.0
    assert result.text == expected


def test_unreadable_crop_scores_below_the_threshold() -> None:
    result = TesseractOcr().recognize(solid(30, height=118, width=1357))

    assert result.confidence < 60.0


def test_parallel_and_sequential_agree_on_real_fixtures() -> None:
    from wuwa_ua.ocr.tesseract import TesseractOcr, preprocess_variants

    image = cv2.imread(str(FIXTURES / "field-01.png"), cv2.IMREAD_COLOR)
    backend = TesseractOcr()

    parallel = backend.recognize(image)
    sequential = max(
        (backend._recognize_prepared(prepared) for prepared in preprocess_variants(image)),
        key=lambda result: result.confidence,
    )

    assert parallel.text == sequential.text
    assert parallel.confidence == sequential.confidence


def test_recognize_still_returns_empty_for_a_blank_crop() -> None:
    from wuwa_ua.ocr.tesseract import TesseractOcr

    result = TesseractOcr().recognize(solid(0, height=118, width=1357))

    assert result.text == ""
