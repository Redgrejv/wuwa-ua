from __future__ import annotations

import signal
import subprocess
import time
from pathlib import Path

PROC = Path("/proc")
POLL_SECONDS = 5.0
SETTLE_SECONDS = 20.0
STOP_TIMEOUT = 10.0


def read_cmdline(directory: Path) -> str:
    try:
        raw = (directory / "cmdline").read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\0", b" ").decode("utf-8", "replace").strip()


def find_game_pids(proc_root: Path, needle: str) -> list[int]:
    target = needle.casefold()
    pids: list[int] = []
    try:
        entries = list(proc_root.iterdir())
    except OSError:
        return []
    for entry in entries:
        if not entry.name.isdigit():
            continue
        if target in read_cmdline(entry).casefold():
            pids.append(int(entry.name))
    return sorted(pids)


class GameWatcher:
    def __init__(
        self,
        process_match: str,
        command: list[str],
        proc_root: Path = PROC,
        poll_seconds: float = POLL_SECONDS,
        settle_seconds: float = SETTLE_SECONDS,
    ) -> None:
        self._process_match = process_match
        self._command = command
        self._proc_root = proc_root
        self._poll_seconds = poll_seconds
        self._settle_seconds = settle_seconds
        self._child: subprocess.Popen[bytes] | None = None

    def running(self) -> bool:
        return bool(find_game_pids(self._proc_root, self._process_match))

    def start_child(self) -> None:
        if self._child is not None and self._child.poll() is None:
            return
        self._child = subprocess.Popen(self._command, start_new_session=True)

    def stop_child(self) -> None:
        if self._child is None:
            return
        if self._child.poll() is None:
            self._child.send_signal(signal.SIGTERM)
            try:
                self._child.wait(timeout=STOP_TIMEOUT)
            except subprocess.TimeoutExpired:
                self._child.kill()
        self._child = None

    def child_alive(self) -> bool:
        return self._child is not None and self._child.poll() is None

    def loop(self) -> None:
        while True:
            if self.running():
                if not self.child_alive():
                    time.sleep(self._settle_seconds)
                    if self.running():
                        self.start_child()
            elif self.child_alive():
                self.stop_child()
            time.sleep(self._poll_seconds)
