from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any

FEMININE = "f"
MASCULINE = "m"
GENDER_TAGS = {FEMININE: "femn", MASCULINE: "masc"}
OTHER_SUBJECTS = {"він", "вона", "воно", "вони", "ти", "ви", "ми"}
SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")
CLAUSE_SPLIT = re.compile(r"([.!?…]+\s+|,\s*|\s+—\s+|;\s*)")
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
NAME_NOISE = re.compile(r"[^^\w\s']+", re.UNICODE)
NAME_CUTOFF = 0.7
NAME_MARGIN = 0.1


def clean_name(name: str) -> str:
    stripped = NAME_NOISE.sub(" ", name)
    tokens = [token for token in stripped.split() if len(token) > 1]
    return " ".join(tokens).casefold()


class Speakers:
    def __init__(self, table: dict[str, str]) -> None:
        self._table = table

    @classmethod
    def load(cls, path: Path) -> Speakers:
        if not path.is_file():
            return cls({})
        table: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split("\t")
            if len(parts) < 2:
                continue
            name = clean_name(parts[0])
            gender = parts[1].strip().casefold()
            if name and gender in GENDER_TAGS:
                table[name] = gender
        return cls(table)

    def gender_of(self, name: str) -> str:
        cleaned = clean_name(name)
        if not cleaned:
            return ""
        direct = self._table.get(cleaned)
        if direct:
            return direct
        scored = sorted(
            (
                (difflib.SequenceMatcher(None, cleaned, name).ratio(), name)
                for name in self._table
            ),
            reverse=True,
        )
        if not scored or scored[0][0] < NAME_CUTOFF:
            return ""
        if len(scored) > 1 and scored[0][0] - scored[1][0] < NAME_MARGIN:
            return ""
        return self._table[scored[0][1]]


def _is_nominative_noun(word: str, morph: Any) -> bool:
    parses = morph.parse(word)
    if any("NPRO" in parse.tag for parse in parses):
        return False
    return any("NOUN" in parse.tag and "nomn" in parse.tag for parse in parses)


def _has_other_subject(clause: str, morph: Any) -> bool:
    words = WORD.findall(clause)
    if any(word.casefold() == "я" for word in words):
        return any(word.casefold() in OTHER_SUBJECTS for word in words)
    for index, word in enumerate(words):
        if word.casefold() in OTHER_SUBJECTS:
            return True
        if index > 0 and word[:1].isupper():
            return True
        if _is_nominative_noun(word, morph):
            return True
    return False


def _past_verb_parse(word: str, morph: Any) -> Any | None:
    for parse in morph.parse(word):
        tag = parse.tag
        if "VERB" in tag and "past" in tag and "plur" not in tag:
            return parse
    return None


def _restore_reflexive(original: str, inflected: str) -> str:
    if original.casefold().endswith("ся") and inflected.casefold().endswith("сь"):
        return inflected[:-2] + "ся"
    return inflected


def _match_case(original: str, replacement: str) -> str:
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _regender_sentence(sentence: str, tag: str, morph: Any) -> str:
    def replace(match: re.Match[str]) -> str:
        word = match.group(0)
        parse = _past_verb_parse(word, morph)
        if parse is None or tag in parse.tag:
            return word
        inflected = parse.inflect({tag})
        if inflected is None:
            return word
        return _match_case(word, _restore_reflexive(word, inflected.word))

    return WORD.sub(replace, sentence)


def regender(text: str, gender: str, morph: Any) -> str:
    tag = GENDER_TAGS.get(gender)
    if tag is None:
        return text

    rebuilt: list[str] = []
    for chunk in CLAUSE_SPLIT.split(text):
        if CLAUSE_SPLIT.fullmatch(chunk) or _has_other_subject(chunk, morph):
            rebuilt.append(chunk)
        else:
            rebuilt.append(_regender_sentence(chunk, tag, morph))
    return "".join(rebuilt)
