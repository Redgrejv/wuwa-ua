from __future__ import annotations

from pathlib import Path

import pytest

from wuwa_ua.control import ControlServer, send_command


def test_server_answers_a_command(tmp_path: Path) -> None:
    server = ControlServer(tmp_path / "sock", lambda command: f"echo:{command}")
    server.start()
    try:
        assert send_command(tmp_path / "sock", "toggle") == "echo:toggle"
    finally:
        server.stop()


def test_server_handles_several_commands_in_a_row(tmp_path: Path) -> None:
    seen: list[str] = []

    def handler(command: str) -> str:
        seen.append(command)
        return "ok"

    server = ControlServer(tmp_path / "sock", handler)
    server.start()
    try:
        for command in ("pause", "resume", "toggle"):
            assert send_command(tmp_path / "sock", command) == "ok"
    finally:
        server.stop()

    assert seen == ["pause", "resume", "toggle"]


def test_stop_removes_the_socket_file(tmp_path: Path) -> None:
    path = tmp_path / "sock"
    server = ControlServer(path, lambda command: "ok")
    server.start()

    assert path.exists()

    server.stop()

    assert not path.exists()


def test_start_replaces_a_stale_socket_file(tmp_path: Path) -> None:
    path = tmp_path / "sock"
    path.write_text("залишок від попереднього запуску", encoding="utf-8")
    server = ControlServer(path, lambda command: "ok")
    server.start()
    try:
        assert send_command(path, "status") == "ok"
    finally:
        server.stop()


def test_sending_to_a_missing_socket_is_reported(tmp_path: Path) -> None:
    with pytest.raises(ConnectionError, match="не запущено"):
        send_command(tmp_path / "nope", "toggle")
