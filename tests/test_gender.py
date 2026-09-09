from __future__ import annotations

from pathlib import Path

import pytest

from wuwa_ua.gender import Speakers, regender

FEMALE = "f"
MALE = "m"


@pytest.fixture(scope="module")
def morph():
    import pymorphy3

    return pymorphy3.MorphAnalyzer(lang="uk")


def test_first_person_past_verb_becomes_feminine(morph) -> None:
    assert regender("Я так втомився.", FEMALE, morph) == "Я так втомилася."


def test_first_person_past_verb_becomes_masculine(morph) -> None:
    assert regender("Я так втомилася.", MALE, morph) == "Я так втомився."


def test_verb_without_a_subject_is_treated_as_the_speaker(morph) -> None:
    assert regender("Втомився чекати.", FEMALE, morph) == "Втомилася чекати."


def test_third_person_she_is_left_alone(morph) -> None:
    assert regender("Вона сказала правду.", MALE, morph) == "Вона сказала правду."


def test_third_person_he_is_left_alone(morph) -> None:
    assert regender("Він сказав правду.", FEMALE, morph) == "Він сказав правду."


def test_second_person_is_left_alone(morph) -> None:
    assert regender("Ти прийшов пізно.", FEMALE, morph) == "Ти прийшов пізно."


def test_named_subject_is_left_alone(morph) -> None:
    assert regender("Мандрівник сказав правду.", FEMALE, morph) == "Мандрівник сказав правду."


def test_present_tense_is_untouched(morph) -> None:
    assert regender("Я йду додому.", FEMALE, morph) == "Я йду додому."


def test_reflexive_ending_stays_full(morph) -> None:
    assert regender("Я повернувся.", FEMALE, morph).endswith("лася.")


def test_only_the_clause_with_the_speaker_changes(morph) -> None:
    text = "Я втомився. Вона сказала правду."

    assert regender(text, FEMALE, morph) == "Я втомилася. Вона сказала правду."


def test_no_gender_leaves_the_text_alone(morph) -> None:
    assert regender("Я втомився.", "", morph) == "Я втомився."


def test_capitalisation_is_preserved(morph) -> None:
    assert regender("Втомився.", FEMALE, morph) == "Втомилася."


def test_speakers_table_reads_names(tmp_path: Path) -> None:
    path = tmp_path / "speakers.tsv"
    path.write_text("# коментар\nJinhsi\tf\nJiyan\tm\n\n", encoding="utf-8")

    speakers = Speakers.load(path)

    assert speakers.gender_of("Jinhsi") == "f"
    assert speakers.gender_of("Jiyan") == "m"


def test_speaker_lookup_ignores_case_and_spacing(tmp_path: Path) -> None:
    path = tmp_path / "speakers.tsv"
    path.write_text("Jinhsi\tf\n", encoding="utf-8")

    assert Speakers.load(path).gender_of("  jinhsi ") == "f"


def test_unknown_speaker_has_no_gender(tmp_path: Path) -> None:
    path = tmp_path / "speakers.tsv"
    path.write_text("Jinhsi\tf\n", encoding="utf-8")

    assert Speakers.load(path).gender_of("Someone Else") == ""


def test_missing_table_is_empty(tmp_path: Path) -> None:
    assert Speakers.load(tmp_path / "nope.tsv").gender_of("Jinhsi") == ""


def test_trailing_ocr_noise_is_stripped(tmp_path: Path) -> None:
    path = tmp_path / "speakers.tsv"
    path.write_text("Jiyan\tm\n", encoding="utf-8")

    assert Speakers.load(path).gender_of("Jiyan /") == "m"


def test_a_slightly_misread_name_still_matches(tmp_path: Path) -> None:
    path = tmp_path / "speakers.tsv"
    path.write_text("Jinhsi\tf\n", encoding="utf-8")

    assert Speakers.load(path).gender_of("Jlnhsi") == "f"


def test_a_badly_misread_name_does_not_match(tmp_path: Path) -> None:
    path = tmp_path / "speakers.tsv"
    path.write_text("Jinhsi\tf\n", encoding="utf-8")

    assert Speakers.load(path).gender_of("Calcharo") == ""


def test_two_word_names_survive_cleaning(tmp_path: Path) -> None:
    path = tmp_path / "speakers.tsv"
    path.write_text("Xiangli Yao\tm\n", encoding="utf-8")

    assert Speakers.load(path).gender_of("Xiangli Yao |") == "m"


def test_verb_agreeing_with_a_noun_is_left_alone(morph) -> None:
    text = "Я пам'ятаю, що у тебе тоді був поганий настрій."

    assert regender(text, FEMALE, morph) == text


def test_both_clauses_of_the_speaker_change(morph) -> None:
    assert regender("Я втомився, бо довго чекав.", FEMALE, morph) == "Я втомилася, бо довго чекала."


def test_a_noun_subject_in_a_later_clause_protects_only_that_clause(morph) -> None:
    result = regender("Я прийшов, але дощ уже почався.", FEMALE, morph)

    assert result.startswith("Я прийшла,")
    assert "дощ уже почався" in result


def test_stray_single_letters_are_dropped(tmp_path: Path) -> None:
    path = tmp_path / "speakers.tsv"
    path.write_text("Qingxiao\tf\n", encoding="utf-8")

    assert Speakers.load(path).gender_of("- ZIngXiao o") == "f"


def test_a_real_one_letter_word_does_not_break_a_two_word_name(tmp_path: Path) -> None:
    path = tmp_path / "speakers.tsv"
    path.write_text("Xiangli Yao\tm\n", encoding="utf-8")

    assert Speakers.load(path).gender_of("Xiangli Yao") == "m"


def test_noise_only_name_matches_nothing(tmp_path: Path) -> None:
    path = tmp_path / "speakers.tsv"
    path.write_text("Qingxiao\tf\n", encoding="utf-8")

    assert Speakers.load(path).gender_of("| . -") == ""


def test_explicit_i_wins_over_a_noun_in_the_same_clause(morph) -> None:
    text = "Ще гірше, я міг би поставити під загрозу справи."

    assert regender(text, FEMALE, morph) == "Ще гірше, я могла би поставити під загрозу справи."


def test_a_clause_without_i_still_protects_its_noun(morph) -> None:
    text = "Я пам'ятаю, що у тебе тоді був поганий настрій."

    assert regender(text, FEMALE, morph) == text


def test_third_person_pronoun_still_wins_over_i(morph) -> None:
    text = "Я знав, що вона прийшла."

    assert regender(text, FEMALE, morph) == "Я знала, що вона прийшла."


def test_a_misread_name_matches_when_the_winner_is_clear(tmp_path: Path) -> None:
    path = tmp_path / "speakers.tsv"
    path.write_text("Qingxiao\tf\nJiyan\tm\nBrant\tm\n", encoding="utf-8")

    assert Speakers.load(path).gender_of("fangxiao") == "f"


def test_an_ambiguous_read_matches_nothing(tmp_path: Path) -> None:
    path = tmp_path / "speakers.tsv"
    path.write_text("Chixia\tf\nChisa\tf\n", encoding="utf-8")

    assert Speakers.load(path).gender_of("chixsa") == ""


def test_an_exact_name_still_wins_over_a_near_twin(tmp_path: Path) -> None:
    path = tmp_path / "speakers.tsv"
    path.write_text("Chixia\tf\nChisa\tm\n", encoding="utf-8")

    assert Speakers.load(path).gender_of("Chixia") == "f"


def test_unknown_speaker_is_logged_for_later(tmp_path: Path) -> None:
    table = tmp_path / "speakers.tsv"
    table.write_text("Jinhsi\tf\n", encoding="utf-8")
    unknown = tmp_path / "speakers-unknown.tsv"
    speakers = Speakers.load(table, unknown_log=unknown)

    speakers.gender_of("Qingxiao")

    assert unknown.read_text(encoding="utf-8").splitlines() == ["qingxiao\t?"]


def test_the_same_unknown_speaker_is_logged_once(tmp_path: Path) -> None:
    table = tmp_path / "speakers.tsv"
    table.write_text("Jinhsi\tf\n", encoding="utf-8")
    unknown = tmp_path / "speakers-unknown.tsv"
    speakers = Speakers.load(table, unknown_log=unknown)

    speakers.gender_of("Qingxiao")
    speakers.gender_of("Qingxiao ")
    speakers.gender_of("Qingxiao")

    assert unknown.read_text(encoding="utf-8").count("qingxiao") == 1


def test_a_known_speaker_is_not_logged(tmp_path: Path) -> None:
    table = tmp_path / "speakers.tsv"
    table.write_text("Jinhsi\tf\n", encoding="utf-8")
    unknown = tmp_path / "speakers-unknown.tsv"
    speakers = Speakers.load(table, unknown_log=unknown)

    speakers.gender_of("Jinhsi")

    assert not unknown.exists()


def test_ocr_noise_is_not_logged_as_a_speaker(tmp_path: Path) -> None:
    table = tmp_path / "speakers.tsv"
    table.write_text("Jinhsi\tf\n", encoding="utf-8")
    unknown = tmp_path / "speakers-unknown.tsv"
    speakers = Speakers.load(table, unknown_log=unknown)

    speakers.gender_of("| . -")
    speakers.gender_of("xy")

    assert not unknown.exists()
