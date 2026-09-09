from __future__ import annotations

from wuwa_ua.display.overlay import needs_preload, plate_geometry, preload_env
from wuwa_ua.types import Region


def test_plate_matches_the_calibrated_band() -> None:
    region = Region(monitor="DP-4", x=0.235, y=0.815, width=0.53, height=0.082)

    left, width, height, bottom_margin = plate_geometry(region, 2560, 1440)

    assert (left, width, height) == (601, 1357, 118)
    assert bottom_margin == 149


def test_plate_top_can_be_lifted_to_the_separator() -> None:
    region = Region(monitor="DP-4", x=0.235, y=0.815, width=0.53, height=0.082)

    _, _, height, bottom_margin = plate_geometry(region, 2560, 1440, top=0.798)

    assert height == 1291 - int(0.798 * 1440)
    assert bottom_margin == 149


def test_a_top_below_the_band_is_ignored() -> None:
    region = Region(monitor="DP-4", x=0.235, y=0.815, width=0.53, height=0.082)

    _, _, plain, _ = plate_geometry(region, 2560, 1440)
    _, _, height, _ = plate_geometry(region, 2560, 1440, top=0.87)

    assert height == plain


def test_plate_height_matches_the_crop_height() -> None:
    region = Region(monitor="DP-4", x=0.235, y=0.815, width=0.53, height=0.082)
    _, crop_top, _, crop_bottom = region.pixels(2560, 1440)

    _, _, height, _ = plate_geometry(region, 2560, 1440)

    assert height == crop_bottom - crop_top


def test_plate_width_matches_the_crop_width() -> None:
    region = Region(monitor="DP-4", x=0.235, y=0.815, width=0.53, height=0.082)
    crop_left, _, crop_right, _ = region.pixels(2560, 1440)

    _, width, _, _ = plate_geometry(region, 2560, 1440)

    assert width == crop_right - crop_left


def test_band_touching_the_bottom_needs_no_margin() -> None:
    region = Region(monitor="DP-4", x=0.0, y=0.9, width=1.0, height=0.1)

    left, width, height, bottom_margin = plate_geometry(region, 2560, 1440)

    assert (left, width, height, bottom_margin) == (0, 2560, 144, 0)


def test_plate_scales_with_the_monitor() -> None:
    region = Region(monitor="DP-4", x=0.0, y=0.5, width=1.0, height=0.25)

    _, width, height, bottom_margin = plate_geometry(region, 1920, 1080)

    assert (width, height, bottom_margin) == (1920, 270, 270)


def test_preload_env_adds_the_layer_shell_library() -> None:
    env = preload_env({"PATH": "/usr/bin"}, "/usr/lib/libgtk4-layer-shell.so")

    assert env["LD_PRELOAD"] == "/usr/lib/libgtk4-layer-shell.so"
    assert env["PATH"] == "/usr/bin"


def test_preload_env_keeps_existing_entries() -> None:
    env = preload_env({"LD_PRELOAD": "/lib/other.so"}, "/usr/lib/libgtk4-layer-shell.so")

    assert env["LD_PRELOAD"] == "/usr/lib/libgtk4-layer-shell.so:/lib/other.so"


def test_preload_env_does_not_duplicate_the_library() -> None:
    env = preload_env(
        {"LD_PRELOAD": "/usr/lib/libgtk4-layer-shell.so"}, "/usr/lib/libgtk4-layer-shell.so"
    )

    assert env["LD_PRELOAD"] == "/usr/lib/libgtk4-layer-shell.so"


def test_preload_is_needed_only_when_absent() -> None:
    assert needs_preload({}, "/usr/lib/libgtk4-layer-shell.so") is True
    assert (
        needs_preload(
            {"LD_PRELOAD": "/usr/lib/libgtk4-layer-shell.so"}, "/usr/lib/libgtk4-layer-shell.so"
        )
        is False
    )
