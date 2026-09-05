from pathlib import Path

from wuwa_ua.translate.glossary import Glossary, build_prompt


def write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "glossary.tsv"
    path.write_text(body, encoding="utf-8")
    return path


def test_missing_file_yields_empty_glossary(tmp_path: Path) -> None:
    glossary = Glossary.load(tmp_path / "nope.tsv")

    assert glossary.entries_for("Rover is here.") == []


def test_matches_entry_present_in_text(tmp_path: Path) -> None:
    glossary = Glossary.load(write(tmp_path, "Rover\tМандрівник\nScar\tШрам\n"))

    assert glossary.entries_for("Rover, wait.") == [("Rover", "Мандрівник")]


def test_ignores_entries_absent_from_text(tmp_path: Path) -> None:
    glossary = Glossary.load(write(tmp_path, "Rover\tМандрівник\nScar\tШрам\n"))

    assert glossary.entries_for("Nothing relevant here.") == []


def test_matching_is_case_insensitive(tmp_path: Path) -> None:
    glossary = Glossary.load(write(tmp_path, "Rover\tМандрівник\n"))

    assert glossary.entries_for("ROVER, wait.") == [("Rover", "Мандрівник")]


def test_matches_whole_words_only(tmp_path: Path) -> None:
    glossary = Glossary.load(write(tmp_path, "Scar\tШрам\n"))

    assert glossary.entries_for("She has a scarf.") == []


def test_skips_comments_and_blank_lines(tmp_path: Path) -> None:
    glossary = Glossary.load(write(tmp_path, "# коментар\n\nRover\tМандрівник\n"))

    assert glossary.entries_for("Rover.") == [("Rover", "Мандрівник")]


def test_skips_malformed_lines(tmp_path: Path) -> None:
    glossary = Glossary.load(write(tmp_path, "broken-line-without-tab\nRover\tМандрівник\n"))

    assert glossary.entries_for("Rover.") == [("Rover", "Мандрівник")]


def test_prompt_contains_the_source_text() -> None:
    prompt = build_prompt("We should go.", context=[], entries=[])

    assert "We should go." in prompt


def test_prompt_lists_glossary_entries() -> None:
    prompt = build_prompt("Rover, wait.", context=[], entries=[("Rover", "Мандрівник")])

    assert "Rover" in prompt
    assert "Мандрівник" in prompt


def test_prompt_includes_context_lines() -> None:
    prompt = build_prompt("And then?", context=["We should go.", "Not yet."], entries=[])

    assert "We should go." in prompt
    assert "Not yet." in prompt


def test_prompt_without_context_omits_the_context_block() -> None:
    prompt = build_prompt("We should go.", context=[], entries=[])

    assert "ПОПЕРЕДНІ РЕПЛІКИ" not in prompt


def test_overlapping_entries_keeps_longest_match(tmp_path: Path) -> None:
    glossary = Glossary.load(write(tmp_path, "Scar\tШрам\nScar of Dawn\tШрам Світанку\n"))

    assert glossary.entries_for("Scar of Dawn is here.") == [("Scar of Dawn", "Шрам Світанку")]


def test_overlapping_entries_keeps_short_when_alone(tmp_path: Path) -> None:
    glossary = Glossary.load(write(tmp_path, "Scar\tШрам\nScar of Dawn\tШрам Світанку\n"))

    assert glossary.entries_for("The Scar is deep.") == [("Scar", "Шрам")]


def test_overlapping_entries_both_present_as_separate_mentions(tmp_path: Path) -> None:
    glossary = Glossary.load(write(tmp_path, "Scar\tШрам\nScar of Dawn\tШрам Світанку\n"))

    assert glossary.entries_for("Scar of Dawn and a small Scar.") == [
        ("Scar", "Шрам"),
        ("Scar of Dawn", "Шрам Світанку"),
    ]
