from __future__ import annotations

import numpy as np

from wuwa_ua.region import crop, plate_crop, render_region_toml
from wuwa_ua.types import Region


def test_crop_returns_the_requested_rectangle() -> None:
    image = np.zeros((1000, 2000, 3), dtype=np.uint8)
    image[800:920, 500:1500] = 255
    region = Region(monitor="DP-4", x=0.25, y=0.8, width=0.5, height=0.12)

    result = crop(image, region)

    assert result.shape == (120, 1000, 3)
    assert int(result.min()) == 255


def test_crop_of_full_frame_is_the_frame() -> None:
    image = np.zeros((100, 200, 3), dtype=np.uint8)
    region = Region(monitor="DP-4", x=0.0, y=0.0, width=1.0, height=1.0)

    assert crop(image, region).shape == image.shape


def test_crop_matches_the_calibrated_subtitle_band() -> None:
    image = np.zeros((1440, 2560, 3), dtype=np.uint8)
    region = Region(monitor="DP-4", x=0.235, y=0.815, width=0.53, height=0.082)

    result = crop(image, region)

    assert result.shape == (118, 1357, 3)


def test_rendered_toml_round_trips() -> None:
    region = Region(monitor="DP-4", x=0.25, y=0.8, width=0.5, height=0.12)

    rendered = render_region_toml(region)

    assert "[region]" in rendered
    assert 'monitor = "DP-4"' in rendered
    assert "x = 0.25" in rendered
    assert "height = 0.12" in rendered


def test_plate_crop_reaches_up_to_the_separator() -> None:
    image = np.zeros((1440, 2560, 3), dtype=np.uint8)
    region = Region(monitor="DP-4", x=0.235, y=0.815, width=0.53, height=0.082)

    result = plate_crop(image, region, 0.798)

    assert result.shape == (1291 - int(0.798 * 1440), 1357, 3)


def test_plate_crop_without_a_top_matches_the_region() -> None:
    image = np.zeros((1440, 2560, 3), dtype=np.uint8)
    region = Region(monitor="DP-4", x=0.235, y=0.815, width=0.53, height=0.082)

    assert plate_crop(image, region, 0.0).shape == crop(image, region).shape


def test_plate_crop_ignores_a_top_below_the_band() -> None:
    image = np.zeros((1440, 2560, 3), dtype=np.uint8)
    region = Region(monitor="DP-4", x=0.235, y=0.815, width=0.53, height=0.082)

    assert plate_crop(image, region, 0.9).shape == crop(image, region).shape
