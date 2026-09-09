from __future__ import annotations

from dataclasses import dataclass

import pytest

from wuwa_ua.translate.errors import TranslationUnavailable
from wuwa_ua.translate.nllb import NllbTranslator, apply_glossary, split_sentences


def test_splits_on_sentence_enders() -> None:
    assert split_sentences("Ready? Then go. Now!") == ["Ready?", "Then go.", "Now!"]


def test_keeps_ellipsis_together() -> None:
    assert split_sentences("*Yawn*... So tired...") == ["*Yawn*...", "So tired..."]


def test_text_without_enders_stays_one_sentence() -> None:
    assert split_sentences("no punctuation here") == ["no punctuation here"]


def test_blank_text_yields_no_sentences() -> None:
    assert split_sentences("   ") == []


def test_glossary_substitutes_target_into_the_source() -> None:
    result = apply_glossary("Rover, the Tacet Discord is close", [("Rover", "Мандрівник")])

    assert result == "Мандрівник, the Tacet Discord is close"


def test_glossary_matches_regardless_of_case() -> None:
    assert apply_glossary("ROVER waits", [("Rover", "Мандрівник")]) == "Мандрівник waits"


def test_glossary_respects_word_boundaries() -> None:
    assert apply_glossary("Rovers gather", [("Rover", "Мандрівник")]) == "Rovers gather"


def test_longer_entries_win_over_their_own_substrings() -> None:
    entries = [("Discord", "Дискорд"), ("Tacet Discord", "Тацетний Дискорд")]

    assert apply_glossary("The Tacet Discord roars", entries) == "The Тацетний Дискорд roars"


@dataclass
class FakeEngine:
    outputs: list[str]
    seen: list[str] | None = None

    def translate(self, sentences: list[str]) -> list[str]:
        if self.seen is None:
            self.seen = []
        self.seen.extend(sentences)
        return self.outputs[: len(sentences)]


def test_translate_joins_the_sentences_back() -> None:
    engine = FakeEngine(outputs=["Перше.", "Друге."])
    translator = NllbTranslator(engine=engine)

    assert translator.translate("First. Second.", context=[], entries=[]) == "Перше. Друге."


def test_translate_applies_the_glossary_before_the_engine_sees_it() -> None:
    engine = FakeEngine(outputs=["Мандрівник чекає."])
    translator = NllbTranslator(engine=engine)

    translator.translate("Rover waits.", context=[], entries=[("Rover", "Мандрівник")])

    assert engine.seen == ["Мандрівник waits."]


def test_empty_text_translates_to_empty_without_touching_the_engine() -> None:
    engine = FakeEngine(outputs=[])
    translator = NllbTranslator(engine=engine)

    assert translator.translate("   ", context=[], entries=[]) == ""
    assert engine.seen in (None, [])


def test_engine_failure_becomes_translation_unavailable() -> None:
    class BrokenEngine:
        def translate(self, sentences: list[str]) -> list[str]:
            raise RuntimeError("модель не завантажилась")

    translator = NllbTranslator(engine=BrokenEngine())

    with pytest.raises(TranslationUnavailable, match="не завантажилась"):
        translator.translate("Anything.", context=[], entries=[])
