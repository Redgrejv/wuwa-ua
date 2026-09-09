from __future__ import annotations

import sys

import pytest

from wuwa_ua.types import Region

def test_plate_rect_matches_the_calibrated_band() -> None:
    from wuwa_ua.display.overlay_windows import plate_rect

    region = Region(monitor="DP-4", x=0.235, y=0.815, width=0.53, height=0.115)

    left, top, width, height = plate_rect(region, 2560, 1440, top=0.798)

    assert (left, width) == (601, 1357)
    assert top == int(0.798 * 1440)
    assert height == int(0.930 * 1440) - top


def test_plate_rect_without_a_top_starts_at_the_band() -> None:
    from wuwa_ua.display.overlay_windows import plate_rect

    region = Region(monitor="DP-4", x=0.0, y=0.5, width=1.0, height=0.25)

    _, top, _, height = plate_rect(region, 1920, 1080)

    assert top == 540
    assert height == 270


@pytest.mark.skipif(sys.platform == "win32", reason="на Windows виклики реальні")
def test_windows_only_helpers_are_not_called_on_linux() -> None:
    from wuwa_ua.display import overlay_windows

    assert hasattr(overlay_windows, "make_click_through")
    assert hasattr(overlay_windows, "hide_from_capture")
