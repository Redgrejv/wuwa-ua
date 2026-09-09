from __future__ import annotations

from wuwa_ua.hotkey import find_windows, matches_window


def test_matches_on_wm_class() -> None:
    assert matches_window("Wuthering Waves", ("steam_app_3513350", "steam_app_3513350"), "steam_app_3513350")


def test_matching_is_case_insensitive() -> None:
    assert matches_window("", ("Steam_App_3513350",), "steam_app_3513350")


def test_matches_on_a_substring_of_the_title() -> None:
    assert matches_window("Wuthering Waves  ", None, "wuthering")


def test_other_windows_do_not_match() -> None:
    assert not matches_window("Firefox", ("firefox", "Firefox"), "steam_app_3513350")


def test_window_without_name_or_class_does_not_match() -> None:
    assert not matches_window(None, None, "steam_app_3513350")


def test_empty_needle_matches_nothing() -> None:
    assert not matches_window("Wuthering Waves", ("steam_app_3513350",), "")


class FakeWindow:
    def __init__(self, name, wm_class, children=()):
        self._name = name
        self._class = wm_class
        self._children = list(children)

    def get_wm_name(self):
        return self._name

    def get_wm_class(self):
        return self._class

    def query_tree(self):
        return type("Tree", (), {"children": self._children})()


def test_every_matching_window_is_found() -> None:
    game_a = FakeWindow("Wuthering Waves", ("steam_app_3513350",))
    game_b = FakeWindow(None, ("steam_app_3513350",))
    root = FakeWindow(None, None, [FakeWindow("Firefox", ("firefox",), [game_b]), game_a])

    found = find_windows(root, "steam_app_3513350")

    assert set(id(window) for window in found) == {id(game_a), id(game_b)}


def test_no_match_gives_an_empty_list() -> None:
    root = FakeWindow(None, None, [FakeWindow("Firefox", ("firefox",))])

    assert find_windows(root, "steam_app_3513350") == []


def test_repeated_press_within_the_debounce_window_is_ignored() -> None:
    from wuwa_ua.hotkey import should_fire

    assert should_fire(now=10.0, last=None, debounce=0.3) is True
    assert should_fire(now=10.1, last=10.0, debounce=0.3) is False
    assert should_fire(now=10.4, last=10.0, debounce=0.3) is True


def test_the_very_first_press_fires_whatever_the_clock_says() -> None:
    from wuwa_ua.hotkey import should_fire

    assert should_fire(now=0.05, last=None, debounce=0.3) is True


def test_listener_accepts_several_bindings() -> None:
    from wuwa_ua.hotkey import HotkeyListener

    calls: list[str] = []
    listener = HotkeyListener(
        "steam_app_3513350",
        {"Page_Up": lambda: calls.append("toggle"), "Home": lambda: calls.append("refresh")},
    )

    assert listener.keys == ["Page_Up", "Home"]


def test_a_binding_without_keys_is_empty() -> None:
    from wuwa_ua.hotkey import HotkeyListener

    assert HotkeyListener("x", {}).keys == []
