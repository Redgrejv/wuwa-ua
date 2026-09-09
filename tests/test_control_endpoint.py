from __future__ import annotations

from pathlib import Path

import pytest

from wuwa_ua.control import ControlServer, send_command
from wuwa_ua.paths import ControlEndpoint


def test_tcp_server_answers_a_command() -> None:
    endpoint = ControlEndpoint(kind="tcp", port=47901)
    server = ControlServer(endpoint, lambda command: f"echo:{command}")
    server.start()
    try:
        assert send_command(endpoint, "toggle") == "echo:toggle"
    finally:
        server.stop()


def test_tcp_server_handles_several_commands(tmp_path: Path) -> None:
    endpoint = ControlEndpoint(kind="tcp", port=47902)
    seen: list[str] = []
    server = ControlServer(endpoint, lambda command: seen.append(command) or "ok")
    server.start()
    try:
        for command in ("pause", "resume", "refresh"):
            assert send_command(endpoint, command) == "ok"
    finally:
        server.stop()

    assert seen == ["pause", "resume", "refresh"]


def test_sending_to_a_dead_tcp_endpoint_is_reported() -> None:
    with pytest.raises(ConnectionError, match="не запущено"):
        send_command(ControlEndpoint(kind="tcp", port=47903), "toggle")


def test_unix_server_still_works(tmp_path: Path) -> None:
    endpoint = ControlEndpoint(kind="unix", path=tmp_path / "sock")
    server = ControlServer(endpoint, lambda command: "ok")
    server.start()
    try:
        assert send_command(endpoint, "status") == "ok"
    finally:
        server.stop()

    assert not endpoint.path.exists()
