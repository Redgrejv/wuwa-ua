from __future__ import annotations

import json
from pathlib import Path

from wuwa_ua.history import HistoryRecord, read_history


def write_records(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


def record(source: str, translation: str, timestamp: float = 1.0) -> dict[str, object]:
    return {
        "timestamp": timestamp,
        "source": source,
        "translation": translation,
        "translated": True,
    }


def test_missing_file_gives_no_records(tmp_path: Path) -> None:
    assert read_history(tmp_path / "nope.jsonl") == []


def test_records_are_read_in_order(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    write_records(path, [record("First.", "Перше.", 1.0), record("Second.", "Друге.", 2.0)])

    records = read_history(path)

    assert [item.translation for item in records] == ["Перше.", "Друге."]
    assert records[0] == HistoryRecord(
        timestamp=1.0, source="First.", translation="Перше.", translated=True
    )


def test_malformed_lines_are_skipped(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    path.write_text(
        json.dumps(record("Good.", "Добре.")) + "\nне json\n{\"broken\": \n",
        encoding="utf-8",
    )

    records = read_history(path)

    assert len(records) == 1
    assert records[0].translation == "Добре."


def test_records_without_the_expected_fields_are_skipped(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    path.write_text(
        json.dumps({"timestamp": 1.0}) + "\n" + json.dumps(record("Good.", "Добре.")) + "\n",
        encoding="utf-8",
    )

    assert len(read_history(path)) == 1


def test_limit_keeps_the_most_recent_records(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    write_records(path, [record(f"Line {index}.", f"Рядок {index}.", float(index)) for index in range(10)])

    records = read_history(path, limit=3)

    assert [item.translation for item in records] == ["Рядок 7.", "Рядок 8.", "Рядок 9."]


def test_untranslated_records_keep_their_flag(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    write_records(path, [{"timestamp": 1.0, "source": "x", "translation": "x", "translated": False}])

    assert read_history(path)[0].translated is False
