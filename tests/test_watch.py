from __future__ import annotations

import signal
from pathlib import Path

from wuwa_ua.watch import find_game_pids, read_cmdline


def make_proc(tmp_path: Path, pid: int, cmdline: str) -> None:
    directory = tmp_path / str(pid)
    directory.mkdir()
    (directory / "cmdline").write_bytes(cmdline.encode("utf-8") + b"\0")


def test_reads_a_null_separated_cmdline(tmp_path: Path) -> None:
    directory = tmp_path / "42"
    directory.mkdir()
    (directory / "cmdline").write_bytes(b"proton\0waitforexitandrun\0game.exe\0")

    assert read_cmdline(directory) == "proton waitforexitandrun game.exe"


def test_missing_cmdline_reads_as_empty(tmp_path: Path) -> None:
    directory = tmp_path / "43"
    directory.mkdir()

    assert read_cmdline(directory) == ""


def test_finds_the_game_process(tmp_path: Path) -> None:
    make_proc(tmp_path, 100, "/usr/bin/firefox")
    make_proc(tmp_path, 200, "proton waitforexitandrun /games/Wuthering Waves/Wuthering Waves.exe")

    assert find_game_pids(tmp_path, "Wuthering Waves.exe") == [200]


def test_matching_ignores_case(tmp_path: Path) -> None:
    make_proc(tmp_path, 300, "/games/WUTHERING WAVES.EXE")

    assert find_game_pids(tmp_path, "wuthering waves.exe") == [300]


def test_no_game_gives_no_pids(tmp_path: Path) -> None:
    make_proc(tmp_path, 100, "/usr/bin/firefox")

    assert find_game_pids(tmp_path, "Wuthering Waves.exe") == []


def test_non_numeric_entries_are_ignored(tmp_path: Path) -> None:
    (tmp_path / "self").mkdir()
    (tmp_path / "meminfo").write_text("x", encoding="utf-8")
    make_proc(tmp_path, 200, "Wuthering Waves.exe")

    assert find_game_pids(tmp_path, "Wuthering Waves.exe") == [200]


def test_pids_come_back_sorted(tmp_path: Path) -> None:
    make_proc(tmp_path, 300, "Wuthering Waves.exe")
    make_proc(tmp_path, 100, "Wuthering Waves.exe")

    assert find_game_pids(tmp_path, "Wuthering Waves.exe") == [100, 300]


class FakeChild:
    def __init__(self, alive: bool = True) -> None:
        self._alive = alive
        self.signals: list[int] = []

    def poll(self):
        return None if self._alive else 0

    def send_signal(self, number: int) -> None:
        self.signals.append(number)
        self._alive = False

    def wait(self, timeout: float | None = None) -> int:
        return 0

    def kill(self) -> None:
        self._alive = False


def test_child_is_not_started_twice(tmp_path: Path, monkeypatch) -> None:
    from wuwa_ua import watch

    make_proc(tmp_path, 200, "Wuthering Waves.exe")
    started: list[list[str]] = []
    monkeypatch.setattr(
        watch.subprocess, "Popen", lambda command, **kwargs: started.append(command) or FakeChild()
    )
    watcher = watch.GameWatcher("Wuthering Waves.exe", ["wuwa-ua", "run"], proc_root=tmp_path)

    watcher.start_child()
    watcher.start_child()

    assert len(started) == 1


def test_stopping_sends_sigterm(tmp_path: Path, monkeypatch) -> None:
    from wuwa_ua import watch

    child = FakeChild()
    monkeypatch.setattr(watch.subprocess, "Popen", lambda command, **kwargs: child)
    watcher = watch.GameWatcher("Wuthering Waves.exe", ["wuwa-ua", "run"], proc_root=tmp_path)
    watcher.start_child()

    watcher.stop_child()

    assert child.signals == [signal.SIGTERM]
    assert watcher.child_alive() is False


def test_running_reflects_the_game_process(tmp_path: Path) -> None:
    from wuwa_ua import watch

    watcher = watch.GameWatcher("Wuthering Waves.exe", ["wuwa-ua", "run"], proc_root=tmp_path)

    assert watcher.running() is False

    make_proc(tmp_path, 200, "Wuthering Waves.exe")

    assert watcher.running() is True


TASKLIST = (
    '"System Idle Process","0","Services","0","8 K"\r\n'
    '"Wuthering Waves.exe","4242","Console","1","3,204,880 K"\r\n'
    '"chrome.exe","1337","Console","1","120,000 K"\r\n'
)


def test_windows_tasklist_is_parsed() -> None:
    from wuwa_ua.watch import parse_tasklist

    assert parse_tasklist(TASKLIST, "Wuthering Waves.exe") == [4242]


def test_windows_tasklist_matching_ignores_case() -> None:
    from wuwa_ua.watch import parse_tasklist

    assert parse_tasklist(TASKLIST, "wuthering waves.exe") == [4242]


def test_windows_tasklist_without_the_game_is_empty() -> None:
    from wuwa_ua.watch import parse_tasklist

    assert parse_tasklist(TASKLIST, "notepad.exe") == []


def test_windows_tasklist_ignores_broken_rows() -> None:
    from wuwa_ua.watch import parse_tasklist

    broken = '"Wuthering Waves.exe"\r\n"Wuthering Waves.exe","x","Console","1","1 K"\r\n'

    assert parse_tasklist(broken, "Wuthering Waves.exe") == []
