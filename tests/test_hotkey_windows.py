from __future__ import annotations

from wuwa_ua.hotkey_windows import WindowsHotkeyListener, virtual_key, window_matches


def test_named_keys_map_to_virtual_codes() -> None:
    assert virtual_key("Page_Up") == 0x21
    assert virtual_key("Home") == 0x24
    assert virtual_key("F9") == 0x78


def test_single_characters_map_to_their_code() -> None:
    assert virtual_key("k") == ord("K")
    assert virtual_key("7") == ord("7")


def test_unknown_key_has_no_code() -> None:
    assert virtual_key("Super_Duper") is None


def test_window_matches_on_a_title_fragment() -> None:
    assert window_matches("Wuthering Waves  ", "wuthering")


def test_window_match_is_case_insensitive() -> None:
    assert window_matches("WUTHERING WAVES", "Wuthering Waves")


def test_other_windows_do_not_match() -> None:
    assert not window_matches("Mozilla Firefox", "wuthering")


def test_empty_needle_matches_nothing() -> None:
    assert not window_matches("Wuthering Waves", "")


def test_listener_reports_its_keys() -> None:
    listener = WindowsHotkeyListener("wuthering", {"Page_Up": lambda: None, "": lambda: None})

    assert listener.keys == ["Page_Up"]
