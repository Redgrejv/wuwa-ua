from __future__ import annotations

import socket
import threading
from collections.abc import Callable
from pathlib import Path

COMMANDS = ("pause", "resume", "toggle", "refresh", "status")
ENCODING = "utf-8"
BUFFER = 4096


class ControlServer:
    def __init__(self, path: Path, handler: Callable[[str], str]) -> None:
        self._path = path
        self._handler = handler
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if self._path.exists():
            self._path.unlink()
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.bind(str(self._path))
        self._socket.listen(4)
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        if self._path.exists():
            self._path.unlink()

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


def send_command(path: Path, command: str) -> str:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.connect(str(path))
    except (FileNotFoundError, ConnectionRefusedError) as exc:
        raise ConnectionError(f"wuwa-ua не запущено ({path})") from exc
    with client:
        client.sendall(command.encode(ENCODING))
        return client.recv(BUFFER).decode(ENCODING).strip()
