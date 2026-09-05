from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from wuwa_ua.normalize import cache_key

SCHEMA = """
CREATE TABLE IF NOT EXISTS translations (
    key TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    translation TEXT NOT NULL
)
"""


class TranslationCache:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self._connection.execute(SCHEMA)
        self._connection.commit()

    def get(self, source: str) -> str | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT translation FROM translations WHERE key = ?",
                (cache_key(source),),
            ).fetchone()
            return None if row is None else str(row[0])

    def put(self, source: str, translation: str) -> None:
        with self._lock:
            self._connection.execute(
                "INSERT INTO translations (key, source, translation) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET translation = excluded.translation, source = excluded.source",
                (cache_key(source), source, translation),
            )
            self._connection.commit()

    def close(self) -> None:
        self._connection.close()
