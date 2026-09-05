import threading
from pathlib import Path
from typing import Optional

from wuwa_ua.translate.cache import TranslationCache


def test_miss_returns_none(tmp_path: Path) -> None:
    cache = TranslationCache(tmp_path / "cache.sqlite")

    assert cache.get("We should go.") is None

    cache.close()


def test_stores_and_returns_translation(tmp_path: Path) -> None:
    cache = TranslationCache(tmp_path / "cache.sqlite")
    cache.put("We should go.", "Нам треба йти.")

    assert cache.get("We should go.") == "Нам треба йти."

    cache.close()


def test_lookup_ignores_case_and_spacing(tmp_path: Path) -> None:
    cache = TranslationCache(tmp_path / "cache.sqlite")
    cache.put("We should go.", "Нам треба йти.")

    assert cache.get("  we  SHOULD go. ") == "Нам треба йти."

    cache.close()


def test_second_put_overwrites(tmp_path: Path) -> None:
    cache = TranslationCache(tmp_path / "cache.sqlite")
    cache.put("We should go.", "Нам треба йти.")
    cache.put("We should go.", "Час рушати.")

    assert cache.get("We should go.") == "Час рушати."

    cache.close()


def test_survives_reopen(tmp_path: Path) -> None:
    path = tmp_path / "cache.sqlite"
    first = TranslationCache(path)
    first.put("We should go.", "Нам треба йти.")
    first.close()

    second = TranslationCache(path)

    assert second.get("We should go.") == "Нам треба йти."

    second.close()


def test_creates_parent_directory(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "deeper" / "cache.sqlite"

    cache = TranslationCache(path)
    cache.put("Hi.", "Привіт.")

    assert path.is_file()

    cache.close()


def test_concurrent_access(tmp_path: Path) -> None:
    cache = TranslationCache(tmp_path / "cache.sqlite")
    exceptions: list[Optional[Exception]] = []
    test_data = {
        "Hello.": "Привіт.",
        "Good morning.": "Доброго ранку.",
        "Goodbye.": "До побачення.",
        "Thank you.": "Дякую.",
        "Please.": "Будь ласка.",
    }

    def writer_thread(thread_id: int) -> None:
        try:
            for iteration in range(20):
                for source, translation in test_data.items():
                    cache.put(source, f"{translation} (t{thread_id}-i{iteration})")
        except Exception as e:
            exceptions.append(e)

    def reader_thread(thread_id: int) -> None:
        try:
            for _ in range(20):
                for source in test_data.keys():
                    result = cache.get(source)
                    assert result is not None or source not in test_data
        except Exception as e:
            exceptions.append(e)

    threads = []
    for i in range(3):
        threads.append(threading.Thread(target=writer_thread, args=(i,)))
        threads.append(threading.Thread(target=reader_thread, args=(i,)))

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert exceptions == [], f"Threads raised exceptions: {exceptions}"

    for source in test_data.keys():
        result = cache.get(source)
        assert result is not None
        assert test_data[source] in result

    cache.close()
