from pathlib import Path

import pytest

from wuwa_ua.config import Config, ConfigError, load_config


def write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(body, encoding="utf-8")
    return path


def test_loads_region_and_applies_defaults(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.25
        y = 0.80
        width = 0.50
        height = 0.12
        """,
    )

    config = load_config(path)

    assert isinstance(config, Config)
    assert config.region.monitor == "DP-4"
    assert config.region.x == 0.25
    assert config.sample_fps == 4.0
    assert config.change_threshold == 3.0
    assert config.stable_frames == 2
    assert config.min_confidence == 60.0
    assert config.translate_timeout == 4.0
    assert config.context_lines == 3
    assert config.display_mode == "window"


def test_overrides_defaults(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0

        [detect]
        change_threshold = 5.5
        stable_frames = 3

        [display]
        mode = "overlay"
        """,
    )

    config = load_config(path)

    assert config.change_threshold == 5.5
    assert config.stable_frames == 3
    assert config.display_mode == "overlay"


def test_missing_region_is_an_error(tmp_path: Path) -> None:
    path = write(tmp_path, "[detect]\nstable_frames = 2\n")

    with pytest.raises(ConfigError, match="region"):
        load_config(path)


def test_region_outside_unit_square_is_an_error(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.9
        y = 0.0
        width = 0.5
        height = 0.1
        """,
    )

    with pytest.raises(ConfigError, match="межі"):
        load_config(path)


def test_unknown_display_mode_is_an_error(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0

        [display]
        mode = "hologram"
        """,
    )

    with pytest.raises(ConfigError, match="hologram"):
        load_config(path)


def test_missing_file_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="не знайдено"):
        load_config(tmp_path / "nope.toml")
