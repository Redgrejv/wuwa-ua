from wuwa_ua.normalize import cache_key, is_meaningful, normalize


def test_collapses_line_breaks_into_spaces() -> None:
    assert normalize("Rover, wait\nfor me here.") == "Rover, wait for me here."


def test_collapses_repeated_whitespace() -> None:
    assert normalize("What   do  you\t\tmean?") == "What do you mean?"


def test_strips_surrounding_whitespace() -> None:
    assert normalize("  Hello.  ") == "Hello."


def test_straightens_curly_quotes_and_dashes() -> None:
    input_str = "“It’s fine” — he said"
    expected = '"It\'s fine" - he said'
    assert normalize(input_str) == expected


def test_joins_hyphen_broken_words() -> None:
    assert normalize("Reso-\nnator") == "Resonator"


def test_drops_control_characters() -> None:
    assert normalize("Clear\x00 sky\x07") == "Clear sky"


def test_empty_text_is_not_meaningful() -> None:
    assert is_meaningful("") is False
    assert is_meaningful("   ") is False


def test_punctuation_noise_is_not_meaningful() -> None:
    assert is_meaningful("|| .. ~") is False


def test_single_character_is_not_meaningful() -> None:
    assert is_meaningful("a") is False


def test_real_sentence_is_meaningful() -> None:
    assert is_meaningful("We should go.") is True


def test_cache_key_ignores_case_and_spacing() -> None:
    assert cache_key("  We SHOULD  go. ") == cache_key("we should go.")