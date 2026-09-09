from __future__ import annotations

import socket
import threading
from collections.abc import Callable

from wuwa_ua.paths import ControlEndpoint

COMMANDS = ("pause", "resume", "toggle", "refresh", "status")
ENCODING = "utf-8"
BUFFER = 4096


def _make_socket(endpoint: ControlEndpoint) -> socket.socket:
    if endpoint.kind == "unix":
        return socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    return socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def _address(endpoint: ControlEndpoint) -> object:
    if endpoint.kind == "unix":
        return str(endpoint.path)
    return (endpoint.host, endpoint.port)


class ControlServer:
    def __init__(self, endpoint: ControlEndpoint, handler: Callable[[str], str]) -> None:
        self._endpoint = endpoint
        self._handler = handler
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        endpoint = self._endpoint
        if endpoint.kind == "unix" and endpoint.path is not None:
            endpoint.path.parent.mkdir(parents=True, exist_ok=True)
            if endpoint.path.exists():
                endpoint.path.unlink()
        self._socket = _make_socket(endpoint)
        if endpoint.kind == "tcp":
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(_address(endpoint))
        self._socket.listen(4)
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        endpoint = self._endpoint
        if endpoint.kind == "unix" and endpoint.path is not None and endpoint.path.exists():
            endpoint.path.unlink()

    def _serve(self) -> None:
        while self._running and self._socket is not None:
            try:
                connection, _ = self._socket.accept()
            except OSError:
                return
            with connection:
                try:
                    payload = connection.recv(BUFFER).decode(ENCODING).strip()
                except OSError:
                    continue
                if not payload:
                    continue
                try:
                    answer = self._handler(payload)
                except Exception as exc:
                    answer = f"помилка: {exc}"
                try:
                    connection.sendall(answer.encode(ENCODING))
                except OSError:
                    continue


def send_command(endpoint: ControlEndpoint, command: str) -> str:
    client = _make_socket(endpoint)
    try:
        client.connect(_address(endpoint))
    except (FileNotFoundError, ConnectionRefusedError, OSError) as exc:
        raise ConnectionError(f"wuwa-ua не запущено ({_address(endpoint)})") from exc
    with client:
        client.sendall(command.encode(ENCODING))
        return client.recv(BUFFER).decode(ENCODING).strip()
