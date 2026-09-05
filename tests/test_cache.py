from pathlib import Path

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
