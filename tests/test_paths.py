from __future__ import annotations

from pathlib import Path

from wuwa_ua.paths import config_dir, control_endpoint, data_dir


def test_linux_uses_xdg_directories() -> None:
    env = {"HOME": "/home/user"}

    assert config_dir("linux", env) == Path("/home/user/.config/wuwa-ua")
    assert data_dir("linux", env) == Path("/home/user/.local/share/wuwa-ua")


def test_linux_honours_xdg_overrides() -> None:
    env = {"HOME": "/home/user", "XDG_CONFIG_HOME": "/cfg", "XDG_DATA_HOME": "/dat"}

    assert config_dir("linux", env) == Path("/cfg/wuwa-ua")
    assert data_dir("linux", env) == Path("/dat/wuwa-ua")


def test_windows_uses_appdata() -> None:
    env = {"APPDATA": r"C:\Users\u\AppData\Roaming", "LOCALAPPDATA": r"C:\Users\u\AppData\Local"}

    assert config_dir("win32", env) == Path(r"C:\Users\u\AppData\Roaming/wuwa-ua")
    assert data_dir("win32", env) == Path(r"C:\Users\u\AppData\Local/wuwa-ua")


def test_windows_without_appdata_falls_back_home() -> None:
    env = {"USERPROFILE": r"C:\Users\u"}

    assert config_dir("win32", env) == Path(r"C:\Users\u/.wuwa-ua")


def test_linux_control_endpoint_is_a_unix_socket() -> None:
    endpoint = control_endpoint("linux", {"XDG_RUNTIME_DIR": "/run/user/1000"})

    assert endpoint.kind == "unix"
    assert endpoint.path == Path("/run/user/1000/wuwa-ua.sock")


def test_windows_control_endpoint_is_a_local_port() -> None:
    endpoint = control_endpoint("win32", {})

    assert endpoint.kind == "tcp"
    assert endpoint.host == "127.0.0.1"
    assert endpoint.port > 0


def test_linux_without_runtime_dir_falls_back_to_tmp() -> None:
    endpoint = control_endpoint("linux", {})

    assert endpoint.path == Path("/tmp/wuwa-ua.sock")
