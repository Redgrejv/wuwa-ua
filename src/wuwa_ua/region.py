from __future__ import annotations

import cv2
import numpy as np

from wuwa_ua.capture.portal import PortalCapture
from wuwa_ua.types import Region

CALIBRATION_WINDOW = "wuwa-ua: виділи зону субтитрів і натисни Enter"


def crop(image: np.ndarray, region: Region) -> np.ndarray:
    height, width = image.shape[:2]
    left, top, right, bottom = region.pixels(width, height)
    return image[top:bottom, left:right]


def plate_crop(image: np.ndarray, region: Region, plate_top: float) -> np.ndarray:
    height, width = image.shape[:2]
    left, top, right, bottom = region.pixels(width, height)
    if plate_top:
        top = min(top, int(plate_top * height))
    return image[top:bottom, left:right]


def render_region_toml(region: Region) -> str:
    return (
        "[region]\n"
        f'monitor = "{region.monitor}"\n'
        f"x = {round(region.x, 4)}\n"
        f"y = {round(region.y, 4)}\n"
        f"width = {round(region.width, 4)}\n"
        f"height = {round(region.height, 4)}\n"
    )


def calibrate(capture: PortalCapture, monitor: str) -> Region:
    frame = next(iter(capture.frames()))
    height, width = frame.image.shape[:2]
    selection = cv2.selectROI(CALIBRATION_WINDOW, frame.image, showCrosshair=False)
    cv2.destroyAllWindows()
    left, top, box_width, box_height = selection
    if box_width == 0 or box_height == 0:
        raise ValueError("зону не виділено")
    return Region(
        monitor=monitor,
        x=left / width,
        y=top / height,
        width=box_width / width,
        height=box_height / height,
    )
