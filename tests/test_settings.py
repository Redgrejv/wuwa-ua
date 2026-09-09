from __future__ import annotations

from pathlib import Path

import pytest

from wuwa_ua.settings import (
    SettingsError,
    is_supported_key,
    read_hotkeys,
    write_hotkeys,
)

CONFIG = """[region]
monitor = "DP-4"
x = 0.235
y = 0.815
width = 0.53
height = 0.107

[hotkey]
key = "Page_Up"
refresh_key = "Page_Down"
history_key = "Home"
window = "steam_app_3513350"

[display]
mode = "overlay"
"""


def make(tmp_path: Path, text: str = CONFIG) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_reads_the_current_hotkeys(tmp_path: Path) -> None:
    assert read_hotkeys(make(tmp_path)) == {"key": "Page_Up", "refresh_key": "Page_Down", "history_key": "Home"}


def test_reads_defaults_when_the_section_is_missing(tmp_path: Path) -> None:
    path = make(tmp_path, "[region]\nmonitor = \"DP-4\"\nx = 0.0\ny = 0.0\nwidth = 1.0\nheight = 1.0\n")

    assert read_hotkeys(path) == {"key": "Page_Up", "refresh_key": "Page_Down", "history_key": "Home"}


def test_writing_changes_only_the_hotkeys(tmp_path: Path) -> None:
    path = make(tmp_path)

    write_hotkeys(path, {"key": "F9", "refresh_key": "F10", "history_key": "F11"})

    text = path.read_text(encoding="utf-8")
    assert 'key = "F9"' in text
    assert 'refresh_key = "F10"' in text
    assert 'window = "steam_app_3513350"' in text
    assert 'mode = "overlay"' in text
    assert "x = 0.235" in text


def test_written_values_can_be_read_back(tmp_path: Path) -> None:
    path = make(tmp_path)

    write_hotkeys(path, {"key": "F9", "refresh_key": "", "history_key": "Home"})

    assert read_hotkeys(path) == {"key": "F9", "refresh_key": "", "history_key": "Home"}


def test_writing_adds_a_missing_section(tmp_path: Path) -> None:
    path = make(tmp_path, "[region]\nmonitor = \"DP-4\"\nx = 0.0\ny = 0.0\nwidth = 1.0\nheight = 1.0\n")

    write_hotkeys(path, {"key": "End", "refresh_key": "Insert", "history_key": "Delete"})

    assert read_hotkeys(path) == {"key": "End", "refresh_key": "Insert", "history_key": "Delete"}


def test_an_empty_key_switches_the_hotkey_off(tmp_path: Path) -> None:
    path = make(tmp_path)

    write_hotkeys(path, {"key": "", "refresh_key": "Page_Down", "history_key": "Home"})

    assert read_hotkeys(path)["key"] == ""


def test_unsupported_key_is_rejected(tmp_path: Path) -> None:
    path = make(tmp_path)

    with pytest.raises(SettingsError, match="Ctrl"):
        write_hotkeys(path, {"key": "Ctrl", "refresh_key": "Page_Down", "history_key": "Home"})


def test_the_same_key_twice_is_rejected(tmp_path: Path) -> None:
    path = make(tmp_path)

    with pytest.raises(SettingsError, match="однакові"):
        write_hotkeys(path, {"key": "Home", "refresh_key": "Home", "history_key": "End"})


def test_supported_keys() -> None:
    assert is_supported_key("Page_Up")
    assert is_supported_key("F9")
    assert is_supported_key("k")
    assert is_supported_key("")
    assert not is_supported_key("Ctrl")
    assert not is_supported_key("Page Up")


def test_latin_letter_is_taken_from_a_cyrillic_keysym() -> None:
    from wuwa_ua.settings import latin_fallback

    assert latin_fallback("Cyrillic_el") == "k"
    assert latin_fallback("Cyrillic_a") == "f"
    assert latin_fallback("Cyrillic_ve") == "d"


def test_latin_fallback_leaves_supported_names_alone() -> None:
    from wuwa_ua.settings import latin_fallback

    assert latin_fallback("Page_Up") == "Page_Up"
    assert latin_fallback("k") == "k"


def test_latin_fallback_gives_up_on_unknown_names() -> None:
    from wuwa_ua.settings import latin_fallback

    assert latin_fallback("Hyper_L") == ""
