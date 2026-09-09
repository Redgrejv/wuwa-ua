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


def test_capture_source_defaults_to_the_game_window(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0
        """,
    )

    assert load_config(path).capture_source == "window"


def test_capture_source_can_fall_back_to_the_monitor(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0

        [capture]
        source = "monitor"
        """,
    )

    assert load_config(path).capture_source == "monitor"


def test_unknown_capture_source_is_an_error(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0

        [capture]
        source = "telepathy"
        """,
    )

    with pytest.raises(ConfigError, match="telepathy"):
        load_config(path)


def test_translate_backend_defaults_to_nllb(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0
        """,
    )

    config = load_config(path)

    assert config.backend == "nllb"
    assert config.model_path.name == "nllb-1.3b"


def test_translate_backend_can_be_ollama(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0

        [translate]
        backend = "ollama"
        model = "gemma3:4b"
        """,
    )

    assert load_config(path).backend == "ollama"


def test_unknown_backend_is_an_error(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0

        [translate]
        backend = "carrier pigeon"
        """,
    )

    with pytest.raises(ConfigError, match="carrier pigeon"):
        load_config(path)


def test_missing_file_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="не знайдено"):
        load_config(tmp_path / "nope.toml")


def test_clear_after_defaults_to_a_second_and_a_half(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0
        """,
    )

    assert load_config(path).clear_after == 1.5


def test_clear_after_can_be_overridden(tmp_path: Path) -> None:
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
        clear_after = 3.0
        """,
    )

    assert load_config(path).clear_after == 3.0


def test_hotkey_defaults_to_page_up_on_the_game_window(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0
        """,
    )

    config = load_config(path)

    assert config.hotkey_key == "Page_Up"
    assert config.hotkey_window == "steam_app_3513350"


def test_hotkey_can_be_changed(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0

        [hotkey]
        key = "F9"
        window = "wuthering"
        """,
    )

    config = load_config(path)

    assert config.hotkey_key == "F9"
    assert config.hotkey_window == "wuthering"


def test_hotkey_can_be_switched_off(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0

        [hotkey]
        key = ""
        """,
    )

    assert load_config(path).hotkey_key == ""


def test_watch_process_defaults_to_the_game_executable(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0
        """,
    )

    assert load_config(path).watch_process == "Wuthering Waves.exe"


def test_watch_process_can_be_changed(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0

        [watch]
        process = "Client-Win64-Shipping.exe"
        """,
    )

    assert load_config(path).watch_process == "Client-Win64-Shipping.exe"


def test_plate_top_defaults_to_off(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0
        """,
    )

    assert load_config(path).plate_top == 0.0


def test_plate_top_is_read_from_display(tmp_path: Path) -> None:
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
        plate_top = 0.798
        """,
    )

    assert load_config(path).plate_top == 0.798


def test_speaker_band_has_defaults(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0
        """,
    )

    config = load_config(path)

    assert config.speaker_y == 0.748
    assert config.speaker_height == 0.044


def test_speaker_band_can_be_moved(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0

        [speaker]
        y = 0.70
        height = 0.05
        """,
    )

    config = load_config(path)

    assert config.speaker_y == 0.70
    assert config.speaker_height == 0.05


def test_speaker_confidence_gate_is_off_by_default(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0
        """,
    )

    config = load_config(path)

    assert config.speaker_min_confidence == 0.0
    assert config.speaker_min_confidence < config.min_confidence


def test_speaker_confidence_can_be_set(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0

        [speaker]
        min_confidence = 45.0
        """,
    )

    assert load_config(path).speaker_min_confidence == 45.0


def test_speaker_band_is_narrower_than_the_subtitle_band(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.235
        y = 0.815
        width = 0.53
        height = 0.082
        """,
    )

    config = load_config(path)

    assert config.speaker_x == 0.33
    assert config.speaker_width == 0.34
    assert config.speaker_width < config.region.width


def test_speaker_band_x_and_width_can_be_set(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0

        [speaker]
        x = 0.40
        width = 0.20
        """,
    )

    config = load_config(path)

    assert config.speaker_x == 0.40
    assert config.speaker_width == 0.20


def test_refresh_and_history_hotkeys_have_defaults(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0
        """,
    )

    config = load_config(path)

    assert config.hotkey_refresh_key == "Page_Down"
    assert config.hotkey_history_key == "Home"


def test_refresh_hotkey_can_be_switched_off(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0

        [hotkey]
        refresh_key = ""
        """,
    )

    assert load_config(path).hotkey_refresh_key == ""


def test_translate_device_defaults_to_cuda(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0
        """,
    )

    config = load_config(path)

    assert config.device == "cuda"
    assert config.beam_size == 4


def test_translate_device_can_be_forced_to_cpu(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0

        [translate]
        device = "cpu"
        beam_size = 2
        """,
    )

    config = load_config(path)

    assert config.device == "cpu"
    assert config.beam_size == 2


def test_unknown_device_is_an_error(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0

        [translate]
        device = "quantum"
        """,
    )

    with pytest.raises(ConfigError, match="quantum"):
        load_config(path)


def test_windows_defaults_are_present(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0
        """,
    )

    config = load_config(path)

    assert config.monitor_index == 1
    assert config.hotkey_window_title == "Wuthering Waves"


def test_windows_settings_can_be_changed(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
        [region]
        monitor = "DP-4"
        x = 0.0
        y = 0.0
        width = 1.0
        height = 1.0

        [capture]
        monitor_index = 2

        [hotkey]
        window_title = "Інша гра"
        """,
    )

    config = load_config(path)

    assert config.monitor_index == 2
    assert config.hotkey_window_title == "Інша гра"
