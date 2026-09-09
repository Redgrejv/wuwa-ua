from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_LIMIT = 500


@dataclass(frozen=True)
class HistoryRecord:
    timestamp: float
    source: str
    translation: str
    translated: bool


def read_history(path: Path, limit: int = DEFAULT_LIMIT) -> list[HistoryRecord]:
    if not path.is_file():
        return []

    records: list[HistoryRecord] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            if "source" not in payload or "translation" not in payload:
                continue
            records.append(
                HistoryRecord(
                    timestamp=float(payload.get("timestamp", 0.0)),
                    source=str(payload["source"]),
                    translation=str(payload["translation"]),
                    translated=bool(payload.get("translated", True)),
                )
            )
    return records[-limit:]
