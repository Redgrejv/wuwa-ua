from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import pytesseract

from wuwa_ua.normalize import normalize
from wuwa_ua.types import OcrResult

UPSCALE = 2
TOPHAT_KERNEL = 31
BRIGHT_THRESHOLD = 200
TESSERACT_CONFIG = "--oem 3 --psm 6"


def _upscaled_gray(crop: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, None, fx=UPSCALE, fy=UPSCALE, interpolation=cv2.INTER_CUBIC)


def preprocess_bright(crop: np.ndarray) -> np.ndarray:
    scaled = _upscaled_gray(crop)
    _, binary = cv2.threshold(scaled, BRIGHT_THRESHOLD, 255, cv2.THRESH_BINARY)
    return cv2.bitwise_not(binary)


def preprocess_tophat(crop: np.ndarray) -> np.ndarray:
    scaled = _upscaled_gray(crop)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (TOPHAT_KERNEL, TOPHAT_KERNEL))
    tophat = cv2.morphologyEx(scaled, cv2.MORPH_TOPHAT, kernel)
    blurred = cv2.bilateralFilter(tophat, 5, 50, 50)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return cv2.bitwise_not(binary)


def preprocess_variants(crop: np.ndarray) -> list[np.ndarray]:
    return [preprocess_bright(crop), preprocess_tophat(crop)]


class TesseractOcr:
    def __init__(self, lang: str = "eng", min_confidence: float = 60.0) -> None:
        self._lang = lang
        self._min_confidence = min_confidence

    def recognize(self, image: np.ndarray) -> OcrResult:
        variants = preprocess_variants(image)
        with ThreadPoolExecutor(max_workers=len(variants)) as pool:
            candidates = list(pool.map(self._recognize_prepared, variants))
        best = OcrResult(text="", confidence=0.0)
        for candidate in candidates:
            if candidate.confidence > best.confidence:
                best = candidate
        return best

    def _recognize_prepared(self, prepared: np.ndarray) -> OcrResult:
        data = pytesseract.image_to_data(
            prepared,
            lang=self._lang,
            config=TESSERACT_CONFIG,
            output_type=pytesseract.Output.DICT,
        )

        words: list[str] = []
        confidences: list[float] = []
        for word, confidence in zip(data["text"], data["conf"], strict=False):
            value = float(confidence)
            if not word.strip() or value < 0:
                continue
            words.append(word)
            confidences.append(value)

        if not words:
            return OcrResult(text="", confidence=0.0)

        return OcrResult(
            text=normalize(" ".join(words)),
            confidence=sum(confidences) / len(confidences),
        )
